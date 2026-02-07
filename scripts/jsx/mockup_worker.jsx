#target photoshop
app.displayDialogs = DialogModes.NO;

/* ============================================================
   SnooozeCo Mockup Worker — DEBUG BUILD
============================================================ */

var SCRIPT_FILE = new File($.fileName);
var PROJECT_ROOT = SCRIPT_FILE.parent.parent.parent;
var JOBS_DIR = new Folder(PROJECT_ROOT.fsName + "/runtime/mockup_jobs");

alert(
    "JSX Worker Paths\n\n" +
    "Script:\n" + SCRIPT_FILE.fsName + "\n\n" +
    "Project root:\n" + PROJECT_ROOT.fsName + "\n\n" +
    "Jobs dir:\n" + JOBS_DIR.fsName
);

/* ============================================================
   Helpers
============================================================ */

function alertDebug(msg) {
    alert("MOCKUP DEBUG\n\n" + msg);
}

function readTextFile(f) {
    if (!(f instanceof File)) f = new File(f);
    if (!f.exists) throw new Error("File not found: " + f.fsName);
    f.encoding = "UTF-8";
    f.open("r");
    var txt = f.read();
    f.close();
    return txt;
}

function parseJson(text) {
    if (typeof JSON !== "undefined" && JSON.parse) {
        return JSON.parse(text);
    }
    return eval("(" + text + ")");
}

function ensureParentFolder(fileObj) {
    var parent = fileObj.parent;
    if (!parent.exists) parent.create();
}

function normalizeName(s) {
    return String(s)
        .replace(/\u00A0/g, " ")
        .replace(/^\s+|\s+$/g, "")   // manual trim
        .replace(/\s+/g, " ")
        .toUpperCase();
}

function listAllFiles(folder) {
    if (!folder.exists) return [];
    var all = folder.getFiles(); // no filter
    var names = [];
    for (var i = 0; i < all.length; i++) {
        try {
            names.push(
                (all[i] instanceof Folder ? "[DIR] " : "[FILE] ") + all[i].name
            );
        } catch (e) {
            names.push("[UNKNOWN ITEM]");
        }
    }
    return names;
}


function waitForJobs(folder, timeoutMs) {
    var start = new Date().getTime();

    while (true) {
        // First: can we see ANYTHING in the folder?
        var allNames = listAllFiles(folder);

        // Second: apply the job filter
        var files = folder.getFiles(function (f) {
            return f instanceof File && /^job_.*\.json$/i.test(f.name);
        });

        if (files.length) {
            return { jobs: files, all: allNames };
        }

        if (new Date().getTime() - start > timeoutMs) {
            return { jobs: [], all: allNames };
        }

        $.sleep(250);
    }
}


/* ============================================================
   LAYER DEBUGGING
============================================================ */

function dumpLayers(container, indent, lines) {
    indent = indent || "";
    lines = lines || [];

    for (var i = 0; i < container.layers.length; i++) {
        var l = container.layers[i];
        var info =
            indent +
            "- [" + l.typename + "] '" +
            l.name +
            "'  (norm='" + normalizeName(l.name) + "')";

        if (l.typename === "ArtLayer") {
            try {
                if (l.smartObject !== undefined) {
                    info += "  [SMART OBJECT]";
                }
            } catch (e) {}
        }

        lines.push(info);

        if (l.typename === "LayerSet") {
            dumpLayers(l, indent + "  ", lines);
        }
    }

    return lines;
}

function findLayerByName(container, name) {
    var target = normalizeName(name);

    for (var i = 0; i < container.layers.length; i++) {
        var layer = container.layers[i];

        if (normalizeName(layer.name) === target) {
            return layer;
        }

        if (layer.typename === "LayerSet") {
            var found = findLayerByName(layer, name);
            if (found) return found;
        }
    }
    return null;
}

/* ============================================================
   Photoshop Actions
============================================================ */

function replaceSmartObjectContents(filePath) {
    var f = (filePath instanceof File) ? filePath : new File(filePath);
    var idReplace = stringIDToTypeID("placedLayerReplaceContents");
    var desc = new ActionDescriptor();
    desc.putPath(charIDToTypeID("null"), f);
    executeAction(idReplace, desc, DialogModes.NO);
}

function resetSmartObjectTransform() {
    var idTrnf = charIDToTypeID("Trnf");
    var desc = new ActionDescriptor();

    desc.putEnumerated(
        charIDToTypeID("FTcs"),
        charIDToTypeID("QCSt"),
        charIDToTypeID("Qcsa")
    );

    desc.putUnitDouble(charIDToTypeID("SclX"), charIDToTypeID("#Prc"), 100);
    desc.putUnitDouble(charIDToTypeID("SclY"), charIDToTypeID("#Prc"), 100);

    executeAction(idTrnf, desc, DialogModes.NO);
}

function exportJpg(doc, outFile, quality) {
    var opts = new ExportOptionsSaveForWeb();
    opts.format = SaveDocumentType.JPEG;
    opts.quality = quality;
    opts.optimized = true;
    opts.includeProfile = false;
    doc.exportDocument(outFile, ExportType.SAVEFORWEB, opts);
}

function getLayerBoundsPx(layer) {
    var b = layer.bounds;
    return {
        left: b[0].value,
        top: b[1].value,
        right: b[2].value,
        bottom: b[3].value,
        width: b[2].value - b[0].value,
        height: b[3].value - b[1].value
    };
}

function fitActiveLayerToTargetBounds(target, mode) {
    // mode: "contain" or "cover"
    var layer = app.activeDocument.activeLayer;

    var lb = getLayerBoundsPx(layer);
    var sx = target.width / lb.width;
    var sy = target.height / lb.height;

    var scale = (mode === "contain")
        ? Math.min(sx, sy)
        : Math.max(sx, sy);

    layer.resize(scale * 100, scale * 100);

    // Center layer inside target bounds
    var newB = getLayerBoundsPx(layer);

    var dx = (target.left + target.width / 2) -
             (newB.left + newB.width / 2);

    var dy = (target.top + target.height / 2) -
             (newB.top + newB.height / 2);

    layer.translate(dx, dy);
}

function fitActiveLayerToCanvas(mode) {
    // mode: "contain" or "cover"
    var doc = app.activeDocument;
    var layer = doc.activeLayer;

    if (!layer || !layer.bounds) {
        throw new Error("No active layer with bounds to fit.");
    }

    var lb = layer.bounds; // [left, top, right, bottom]
    var lw = lb[2].value - lb[0].value;
    var lh = lb[3].value - lb[1].value;

    var dw = doc.width.value;
    var dh = doc.height.value;

    var sx = dw / lw;
    var sy = dh / lh;

    var scale = (mode === "contain") ? Math.min(sx, sy) : Math.max(sx, sy);

    // AnchorPosition enums are unreliable — use center via percentages
    layer.resize(scale * 100, scale * 100);
}

/* ============================================================
   Job Processing
============================================================ */

function processJob(jobFile) {
    var job = parseJson(readTextFile(jobFile));

    var soName = job.smart_object_layer || "ARTWORK";

    var psdFile = new File(job.template_psd);
    var tiffFile = new File(job.poster_tiff);
    var outFile = new File(job.output_jpg);

    if (!psdFile.exists) throw new Error("Template PSD missing:\n" + psdFile.fsName);
    if (!tiffFile.exists) throw new Error("Poster TIFF missing:\n" + tiffFile.fsName);

    ensureParentFolder(outFile);

    var doc = app.open(psdFile);

    /* ---------- HARD PROOF ---------- */
    alertDebug(
        "Opened PSD:\n" +
        doc.fullName.fsName +
        "\n\nLooking for layer:\n'" + soName + "'"
    );

    var allLayers = dumpLayers(doc);
    alertDebug(
        "Layers seen by JSX:\n\n" + allLayers.join("\n")
    );

    var layer = findLayerByName(doc, soName);

    if (!layer) {
        doc.close(SaveOptions.DONOTSAVECHANGES);
        throw new Error(
            "Layer '" + soName + "' NOT FOUND.\n\n" +
            "Layers detected:\n\n" +
            allLayers.join("\n")
        );
    }

    app.activeDocument = doc;
    doc.activeLayer = layer;

    app.activeDocument = doc;
    doc.activeLayer = layer;

    // Attempt replace — this ONLY works on Smart Objects
    try {
        replaceSmartObjectContents(tiffFile);
    } catch (e) {
        doc.close(SaveOptions.DONOTSAVECHANGES);
        throw new Error(
            "Layer '" + layer.name + "' is not a replaceable Smart Object.\n\n" +
            "Photoshop error:\n" + e.message
        );
    }

    var targetBounds = getLayerBoundsPx(layer);
    replaceSmartObjectContents(tiffFile);
    resetSmartObjectTransform();
    fitActiveLayerToTargetBounds(targetBounds, "cover");


    exportJpg(doc, outFile, job.jpg_quality || 92);

    doc.close(SaveOptions.DONOTSAVECHANGES);
}

/* ============================================================
   MAIN
============================================================ */

function main() {
    var res = waitForJobs(JOBS_DIR, 15000); // wait up to 15 seconds
    var files = res.jobs;

    if (!files.length) {
        alertDebug(
            "No job files found after waiting.\n\n" +
            "Folder:\n" + JOBS_DIR.fsName + "\n\n" +
            "Folder exists: " + JOBS_DIR.exists + "\n\n" +
            "Items visible to JSX (" + res.all.length + "):\n\n" +
            (res.all.length ? res.all.join("\n") : "(none)")
        );
        return;
    }

    var matched = [];
    for (var i = 0; i < files.length; i++) matched.push(files[i].name);
    alertDebug("Jobs matched:\n\n" + matched.join("\n"));

    for (var j = 0; j < files.length; j++) {
        processJob(files[j]);
        try { files[j].remove(); } catch (e) {}
    }
}

try {
    main();
} catch (err) {
    alert("Mockup Worker ERROR:\n\n" + err.message);
}
