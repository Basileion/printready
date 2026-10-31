/* PrintReady AI /check/ page: UI + tiny WebGL viewer. Parsing/analysis runs in a Web Worker (../js/meshcheck.js).
 * Nothing is uploaded. Beacon events carry only the file extension and the overall verdict (no names, no sizes). */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var fileIn = $("file"), drop = $("drop"), status = $("status"), unitsSel = $("units"), targetIn = $("target"), upSel = $("up");
  var worker = null, haveMesh = false, ext = "", busy = false, autoScaled = false, sentResult = false;
  function track(ev, cta) { try { if (window.grow) window.grow.track(ev, cta); } catch (e) {} }

  function getWorker() {
    if (worker) return worker;
    worker = new Worker("../js/meshcheck.js");
    worker.onmessage = onResult;
    worker.onerror = function (e) { busy = false; setStatus("Could not read this file: " + (e.message || "worker error"), true); track("calculator_use", "check_error"); };
    return worker;
  }
  function setStatus(t, err) { status.textContent = t; status.style.color = err ? "var(--ds-neg)" : ""; }
  function opts() {
    var u = unitsSel.value, o = { upAxis: upSel.value === "auto" ? undefined : upSel.value };
    if (u === "target") o.targetLongestMm = Math.max(1, +targetIn.value || 50);
    else if (u !== "auto") o.units = u;
    if (autoScaled && u === "auto") o.targetLongestMm = 50;
    return o;
  }
  function run(buffer, name) {
    busy = true; var w = getWorker(), o = opts();
    if (buffer) { o.buffer = buffer; o.name = name; w.postMessage(o, [buffer]); } else w.postMessage(o);
  }
  function loadBuffer(buf, name, label) {
    ext = (name.split(".").pop() || "").toLowerCase();
    if (["stl", "obj", "glb", "gltf"].indexOf(ext) < 0) { setStatus("Unsupported file type. Use .stl, .obj, .glb or .gltf.", true); return; }
    autoScaled = false; sentResult = false; haveMesh = true;
    track("calculator_use", "check_file_loaded:" + ext);
    setStatus("Checking " + label + " in your browser…");
    run(buf, name);
  }
  function handleFile(f) {
    if (!f) return;
    if (f.size > 300 * 1024 * 1024) { setStatus("That file is over 300 MB; try a decimated copy.", true); return; }
    setStatus("Reading file locally…");
    f.arrayBuffer().then(function (b) { loadBuffer(b, f.name, "your file"); }, function () { setStatus("Could not read the file.", true); });
  }
  fileIn.addEventListener("change", function () { handleFile(fileIn.files[0]); fileIn.value = ""; });
  ["dragenter", "dragover"].forEach(function (t) { drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.add("over"); }); });
  ["dragleave", "drop"].forEach(function (t) { drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.remove("over"); }); });
  drop.addEventListener("drop", function (e) { var f = e.dataTransfer && e.dataTransfer.files[0]; handleFile(f); });
  document.querySelectorAll("[data-sample]").forEach(function (b) {
    b.addEventListener("click", function () {
      var url = b.getAttribute("data-sample"), sid = b.getAttribute("data-sid");
      setStatus("Downloading sample mesh from this site…");
      track("calculator_use", "check_sample:" + sid);
      fetch(url).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        if (/\.gz$/.test(url) && typeof DecompressionStream === "function") return new Response(r.body.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
        return r.arrayBuffer();
      }).then(function (buf) { loadBuffer(buf, url.replace(/\.gz$/, "").split("/").pop(), b.textContent.replace(/\s*\(.*\)/, "")); })
        .catch(function (e) { setStatus("Could not load the sample (" + e.message + ").", true); });
    });
  });
  unitsSel.addEventListener("change", function () { targetIn.disabled = unitsSel.value !== "target"; autoScaled = false; if (haveMesh && !busy) run(); });
  targetIn.addEventListener("change", function () { if (haveMesh && !busy && unitsSel.value === "target") run(); });
  upSel.addEventListener("change", function () { if (haveMesh && !busy) run(); });

  var LABEL = { pass: "Pass", warn: "Warn", fail: "Fail" };
  var TITLE = { pass: "Looks printable (geometry)", warn: "Printable, with things to check", fail: "Fix before you slice" };
  function fmt(n) { return n == null ? "–" : Number(n).toLocaleString("en-US"); }
  function onResult(ev) {
    busy = false;
    var d = ev.data;
    if (!d.ok) { setStatus(d.error, true); track("calculator_use", "check_error"); return; }
    var r = d.result, L = Math.max.apply(null, r.dimsMm);
    if (unitsSel.value === "auto" && !autoScaled && (L > 1000 || L < 1)) { autoScaled = true; run(); return; }
    setStatus((autoScaled ? "The file’s size looks unit-less (common for AI exports), so we scaled its longest edge to 50 mm, like our benchmark. Change it under Size / units. " : "") +
      "Checked " + fmt(r.triangles) + " triangles in " + (r.ms / 1000).toFixed(1) + " s, locally.");
    var vl = $("vlist"); vl.innerHTML = "";
    r.verdicts.forEach(function (v) {
      var li = document.createElement("li");
      li.innerHTML = '<span class="badge b-' + v.level + '">' + LABEL[v.level] + "</span><b></b><p></p>" + (v.fix ? '<p class="fix"></p>' : "");
      li.querySelector("b").textContent = v.title;
      li.querySelectorAll("p")[0].textContent = v.detail;
      if (v.fix) li.querySelector(".fix").textContent = "Fix: " + v.fix;
      vl.appendChild(li);
    });
    var ob = $("overall-badge"); ob.className = "badge b-" + r.overall; ob.textContent = LABEL[r.overall];
    $("overall-title").textContent = TITLE[r.overall];
    var rows = [["Triangles", fmt(r.triangles)], ["Size (X × Y × Z)", r.dimsMm.join(" × ") + " mm"], ["Up axis", r.upAxis + "-up"],
      ["Volume", r.volumeMm3 != null ? fmt(Math.abs(Math.round(r.volumeMm3))) + " mm³ (" + (Math.abs(r.volumeMm3) / 1000).toFixed(1) + " cm³)" : "n/a until watertight"],
      ["Open edges (holes)", fmt(r.boundaryEdges)], ["Edges shared by 3+ faces", fmt(r.nonManifoldEdges)], ["Parts", fmt(r.parts)], ["Zero-area faces", fmt(r.degenerateFaces)]];
    var tb = $("stats").querySelector("tbody"); tb.innerHTML = "";
    rows.forEach(function (rw) { var tr = document.createElement("tr"); tr.innerHTML = "<td></td><td class='num'></td>"; tr.children[0].textContent = rw[0]; tr.children[1].textContent = rw[1]; tb.appendChild(tr); });
    $("results").hidden = false;
    try { viewer(d.preview, r); } catch (e) { $("viewer").hidden = true; }
    if (!sentResult) { sentResult = true; track("calculator_use", "check_result:" + r.overall + ":" + ext); $("results").scrollIntoView({ behavior: "smooth", block: "start" }); }
  }

  /* ---------- minimal WebGL viewer ---------- */
  var V = null;
  function viewer(pv, r) {
    var canvas = $("gl");
    if (!V) {
      var gl = canvas.getContext("webgl", { antialias: true }) || canvas.getContext("experimental-webgl");
      if (!gl) { $("viewer").hidden = true; return; }
      var u32 = gl.getExtension("OES_element_index_uint");
      function sh(type, src) { var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; }
      function prog(vs, fs) { var p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p); return p; }
      var meshP = prog("attribute vec3 p;attribute vec3 n;uniform mat4 M;uniform mat3 R;varying vec3 vn;void main(){vn=R*n;gl_Position=M*vec4(p,1.0);}",
        "precision mediump float;varying vec3 vn;void main(){vec3 N=normalize(vn);float d=abs(N.z)*0.6+0.25+0.15*max(N.y,0.0);gl_FragColor=vec4(vec3(0.80,0.83,0.88)*d,1.0);}");
      var lineP = prog("attribute vec3 p;attribute float k;uniform mat4 M;varying float vk;void main(){vk=k;gl_PointSize=5.0;gl_Position=M*vec4(p,1.0);}",
        "precision mediump float;varying float vk;void main(){gl_FragColor=vk<1.5?vec4(0.86,0.15,0.15,1.0):vec4(0.95,0.55,0.05,1.0);}");
      V = { gl: gl, u32: u32, meshP: meshP, lineP: lineP, yaw: -0.6, pitch: 0.5, zoom: 1, bufs: {} };
      var drag = null;
      canvas.addEventListener("pointerdown", function (e) { drag = [e.clientX, e.clientY]; canvas.setPointerCapture(e.pointerId); canvas.style.cursor = "grabbing"; });
      canvas.addEventListener("pointermove", function (e) { if (!drag) return; V.yaw += (e.clientX - drag[0]) * 0.01; V.pitch = Math.max(-1.5, Math.min(1.5, V.pitch + (e.clientY - drag[1]) * 0.01)); drag = [e.clientX, e.clientY]; draw(); });
      canvas.addEventListener("pointerup", function () { drag = null; canvas.style.cursor = ""; });
      canvas.addEventListener("wheel", function (e) { e.preventDefault(); V.zoom = Math.max(0.2, Math.min(5, V.zoom * (e.deltaY > 0 ? 1.1 : 0.9))); draw(); }, { passive: false });
      window.addEventListener("resize", draw);
    }
    var gl = V.gl, P = pv.positions, I = pv.indices;
    if (!V.u32 && P.length / 3 > 65535) { $("viewer").hidden = true; return; }
    $("viewer").hidden = false;
    // area-weighted vertex normals
    var N = new Float32Array(P.length);
    for (var f = 0; f < I.length; f += 3) {
      var a = I[f] * 3, b = I[f + 1] * 3, c = I[f + 2] * 3;
      var ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2], vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
      var nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      N[a] += nx; N[a + 1] += ny; N[a + 2] += nz; N[b] += nx; N[b + 1] += ny; N[b + 2] += nz; N[c] += nx; N[c + 1] += ny; N[c + 2] += nz;
    }
    function buf(name, target, data) { var bb = V.bufs[name] || (V.bufs[name] = gl.createBuffer()); gl.bindBuffer(target, bb); gl.bufferData(target, data, gl.STATIC_DRAW); }
    buf("p", gl.ARRAY_BUFFER, P); buf("n", gl.ARRAY_BUFFER, N);
    buf("i", gl.ELEMENT_ARRAY_BUFFER, V.u32 ? I : new Uint16Array(I));
    var E = pv.badEdges, K = pv.badKind, LP = new Float32Array(E.length * 3), LK = new Float32Array(E.length);
    for (var e = 0; e < E.length; e++) { LP[e * 3] = P[E[e] * 3]; LP[e * 3 + 1] = P[E[e] * 3 + 1]; LP[e * 3 + 2] = P[E[e] * 3 + 2]; LK[e] = K[e >> 1]; }
    buf("lp", gl.ARRAY_BUFFER, LP); buf("lk", gl.ARRAY_BUFFER, LK);
    V.nIdx = I.length; V.nLines = E.length; V.center = [r.dimsMm[0] / 2, r.dimsMm[1] / 2, r.dimsMm[2] / 2];
    V.radius = Math.max(1e-6, Math.sqrt(r.dimsMm[0] * r.dimsMm[0] + r.dimsMm[1] * r.dimsMm[1] + r.dimsMm[2] * r.dimsMm[2]) / 2);
    $("legend").textContent = (r.boundaryEdges + r.nonManifoldEdges ? "Red = open edges · orange = 3+ faces · " : "") + "drag to rotate";
    draw();
  }
  function mul(a, b) { var o = new Float32Array(16); for (var i = 0; i < 4; i++) for (var j = 0; j < 4; j++) { var s = 0; for (var k = 0; k < 4; k++) s += a[k * 4 + j] * b[i * 4 + k]; o[i * 4 + j] = s; } return o; }
  function draw() {
    if (!V || V.nIdx == null) return;
    var gl = V.gl, cv = gl.canvas, dpr = Math.min(2, window.devicePixelRatio || 1);
    var w = Math.max(1, Math.round(cv.clientWidth * dpr)), h = Math.max(1, Math.round(cv.clientHeight * dpr));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    gl.viewport(0, 0, w, h); gl.clearColor(0.96, 0.96, 0.97, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    // view: translate -center, rotate Z by yaw, tilt so Z-up shows upright, then push back
    var cy = Math.cos(V.yaw), sy = Math.sin(V.yaw), cp = Math.cos(V.pitch), sp = Math.sin(V.pitch);
    var T = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -V.center[0], -V.center[1], -V.center[2], 1]);
    var Rz = new Float32Array([cy, sy, 0, 0, -sy, cy, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
    // map world Z-up to view Y-up, then pitch about X
    var Rx = new Float32Array([1, 0, 0, 0, 0, sp, -cp, 0, 0, cp, sp, 0, 0, 0, 0, 1]);
    var dist = V.radius * 2.6 * V.zoom;
    var Tz = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, -dist, 1]);
    var f = 1 / Math.tan(0.35), aspect = w / h, near = Math.max(dist - V.radius * 2, dist * 0.01), far = dist + V.radius * 2;
    var Pm = new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) / (near - far), -1, 0, 0, 2 * far * near / (near - far), 0]);
    var RV = mul(Rx, Rz), MV = mul(Tz, mul(RV, T)), M = mul(Pm, MV);
    var R3 = new Float32Array([RV[0], RV[1], RV[2], RV[4], RV[5], RV[6], RV[8], RV[9], RV[10]]);
    gl.enable(gl.DEPTH_TEST);
    gl.useProgram(V.meshP);
    gl.uniformMatrix4fv(gl.getUniformLocation(V.meshP, "M"), false, M);
    gl.uniformMatrix3fv(gl.getUniformLocation(V.meshP, "R"), false, R3);
    var lp = gl.getAttribLocation(V.meshP, "p"), ln = gl.getAttribLocation(V.meshP, "n");
    gl.bindBuffer(gl.ARRAY_BUFFER, V.bufs.p); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, V.bufs.n); gl.enableVertexAttribArray(ln); gl.vertexAttribPointer(ln, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, V.bufs.i);
    gl.drawElements(gl.TRIANGLES, V.nIdx, V.u32 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT, 0);
    gl.disableVertexAttribArray(ln);
    if (V.nLines) {
      gl.disable(gl.DEPTH_TEST);
      gl.useProgram(V.lineP);
      gl.uniformMatrix4fv(gl.getUniformLocation(V.lineP, "M"), false, M);
      var pp = gl.getAttribLocation(V.lineP, "p"), pk = gl.getAttribLocation(V.lineP, "k");
      gl.bindBuffer(gl.ARRAY_BUFFER, V.bufs.lp); gl.enableVertexAttribArray(pp); gl.vertexAttribPointer(pp, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, V.bufs.lk); gl.enableVertexAttribArray(pk); gl.vertexAttribPointer(pk, 1, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.LINES, 0, V.nLines);
      gl.drawArrays(gl.POINTS, 0, V.nLines);
      gl.disableVertexAttribArray(pk);
    }
  }
})();
