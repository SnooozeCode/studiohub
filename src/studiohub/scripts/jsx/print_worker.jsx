#target photoshop
app.displayDialogs = DialogModes.NO;

/* ==========================================
   SnooozeCo — 2-Up Job Queue Worker
   ========================================== */

// NOTE:
// We intentionally duplicate + flatten + copy instead of layer.duplicate()
// due to Photoshop frontmost-document constraints and Select All Layers
// being unavailable in many environments. This method is version-safe.

// ==========================================
// Resolve app runtime/print_jobs dynamically
// ==========================================

// Path to the JSX file itself
var jsxFile = new File($.fileName);

// <APP_ROOT>/scripts/jsx/print_worker.jsx
var APP_ROOT = jsxFile.parent.parent.parent;

// <APP_ROOT>/runtime/print_jobs
var JOB_QUEUE_DIR = new Folder(APP_ROOT + "/runtime/print_jobs");

if (!JOB_QUEUE_DIR.exists) {
    throw new Error("JOB_QUEUE_DIR not found:\n" + JOB_QUEUE_DIR.fsName);
}

/* ============================
   FILE HELPERS
============================ */

function listJobFiles(folder) {
    var files = folder.getFiles(function (f) {
        return f instanceof File && /job_\d{4}\.txt$/i.test(f.name);
    });

    files.sort(function (a, b) {
        return a.name.toLowerCase() > b.name.toLowerCase() ? 1 : -1;
    });

    return files;
}

function readLines(fileObj) {
    fileObj.open("r");
    var lines = [];
    while (!fileObj.eof) {
        var line = fileObj.readln().replace(/^\s+|\s+$/g, "");
        if (line.length) lines.push(line);
    }
    fileObj.close();
    return lines;
}

function safeRemove(fileObj) {
    try { fileObj.remove(); } catch (e) {}
}

/* ============================
   IMAGE HELPERS
============================ */

function normalizeToPortraitIfNeeded(doc) {
    if (doc.width.as("px") > doc.height.as("px")) {
        doc.rotateCanvas(90);
    }
}

function pasteFlattenedCopy(sourceDoc, targetDoc) {
    // Duplicate doc safely
    var temp = sourceDoc.duplicate("__TEMP_FLATTEN__", false);
    app.activeDocument = temp;

    temp.flatten();

    // Copy merged pixels
    temp.selection.selectAll();
    temp.selection.copy();

    temp.close(SaveOptions.DONOTSAVECHANGES);

    // Paste into target
    app.activeDocument = targetDoc;
    targetDoc.paste();

    return targetDoc.activeLayer;
}

function fitLayerToRect(layer, rectX, rectY, rectW, rectH) {
    var b = layer.bounds;
    var w = b[2].as("px") - b[0].as("px");
    var h = b[3].as("px") - b[1].as("px");

    var scale = Math.min((rectW / w), (rectH / h)) * 100;
    layer.resize(scale, scale, AnchorPosition.MIDDLECENTER);

    b = layer.bounds;
    var cx = b[0].as("px") + (b[2].as("px") - b[0].as("px")) / 2;
    var cy = b[1].as("px") + (b[3].as("px") - b[1].as("px")) / 2;

    layer.translate(
        rectX + rectW / 2 - cx,
        rectY + rectH / 2 - cy
    );
}

/* ============================
   JOB ACTIONS
============================ */

function openSingle(path) {
    var file = new File(path);
    if (!file.exists) {
        alert("File not found:\n" + file.fsName);
        return;
    }

    app.open(file);
}

function generate2Up(pathA, pathB) {
    var fileA = new File(pathA);
    var fileB = new File(pathB);

    if (!fileA.exists) {
        alert("File not found:\n" + fileA.fsName);
        return;
    }

    var sameFile = fileA.fsName.toLowerCase() === fileB.fsName.toLowerCase();

    var docA = app.open(fileA);
    normalizeToPortraitIfNeeded(docA);

    var docB = null;
    if (!sameFile) {
        if (!fileB.exists) {
            docA.close(SaveOptions.DONOTSAVECHANGES);
            alert("File not found:\n" + fileB.fsName);
            return;
        }
        docB = app.open(fileB);
        normalizeToPortraitIfNeeded(docB);
    }

    var dpi = docA.resolution;
    var twoUp = app.documents.add(
        Math.round(24 * dpi),
        Math.round(18 * dpi),
        dpi,
        "__SNOOOZECO_2UP__",
        NewDocumentMode.RGB,
        DocumentFill.WHITE
    );

    var slotW = Math.round(12 * dpi);
    var slotH = Math.round(18 * dpi);

    // LEFT
    var leftLayer = pasteFlattenedCopy(docA, twoUp);
    fitLayerToRect(leftLayer, 0, 0, slotW, slotH);

    // RIGHT
    if (sameFile) {
        var rightLayer = pasteFlattenedCopy(docA, twoUp);
    } else {
        var rightLayer = pasteFlattenedCopy(docB, twoUp);
    }

    fitLayerToRect(rightLayer, slotW, 0, slotW, slotH);

    docA.close(SaveOptions.DONOTSAVECHANGES);
    if (docB) docB.close(SaveOptions.DONOTSAVECHANGES);

    twoUp.flatten();
}

/* ============================
   MAIN: DRAIN QUEUE
============================ */

var jobFiles = listJobFiles(JOB_QUEUE_DIR);

for (var i = 0; i < jobFiles.length; i++) {
    var jf = jobFiles[i];

    try {
        var lines = readLines(jf);

        if (lines.length === 1) {
            openSingle(lines[0]);

        } else if (lines.length === 2) {
            generate2Up(lines[0], lines[1]);

        } else {
            alert("Invalid job file:\n" + jf.fsName);
        }

    } catch (e) {
        alert("Job failed:\n\n" + jf.fsName + "\n\n" + e);
    }

    safeRemove(jf);
}
