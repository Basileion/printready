/* PrintReady AI mesh checker: parses STL (binary/ASCII), OBJ, GLB/glTF (embedded buffers) and runs
 * geometry checks fully client-side. No network, no uploads. Works in browser, Web Worker and Node.
 * Checks mirror rubric v0.2 (pipeline/score_v02.py) where they overlap:
 *   - zero-area / index-degenerate faces dropped first ("export padding"), as drop_export_padding()
 *   - watertight = every edge shared by exactly 2 faces (trimesh is_watertight)
 *   - non-manifold edge count = edges NOT shared by exactly 2 faces (count_nonmanifold_edges):
 *     0 -> full points, 1-5 -> half, >5 -> zero
 *   - body count = connected parts (trimesh body_count)
 *   - bed contact = area of down-facing faces (nz < -0.7) within 0.2 mm of the bed (first_layer_area);
 *     10 mm^2 -> 0 points, 100 mm^2 -> full
 *   - glTF/GLB is Y-up, STL/OBJ Z-up (UP_AXIS)
 * Not checked here (needs a slicer or ray casting): wall thickness, self-intersections, supports, slicing. */
(function (root) {
  "use strict";
  var A1_BED_MM = [256, 256, 256];
  var BED_BAND_MM = 0.2;
  var CONTACT_ZERO_MM2 = 10, CONTACT_FULL_MM2 = 100;
  var UNIT_MM = { mm: 1, cm: 10, m: 1000, in: 25.4 };

  /* ---------- parsers: return {positions: Float32Array(xyz...), indices: Uint32Array|null} ---------- */
  function isBinarySTL(buf) {
    if (buf.byteLength < 84) return false;
    var dv = new DataView(buf);
    var n = dv.getUint32(80, true);
    if (84 + n * 50 === buf.byteLength) return true;
    var head = new Uint8Array(buf, 0, Math.min(buf.byteLength, 512));
    var s = ""; for (var i = 0; i < head.length; i++) s += String.fromCharCode(head[i]);
    if (/^\s*solid[\s\S]*facet/.test(s)) return false;
    return 84 + n * 50 <= buf.byteLength;
  }
  function parseSTL(buf) {
    if (isBinarySTL(buf)) {
      var dv = new DataView(buf), n = dv.getUint32(80, true), pos = new Float32Array(n * 9), o = 84;
      for (var t = 0; t < n; t++, o += 50) for (var k = 0; k < 9; k++) pos[t * 9 + k] = dv.getFloat32(o + 12 + k * 4, true);
      return { positions: pos, indices: null, format: "stl-binary" };
    }
    var text = new TextDecoder().decode(new Uint8Array(buf));
    var re = /vertex\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)/g, m, out = [];
    while ((m = re.exec(text))) out.push(+m[1], +m[2], +m[3]);
    if (!out.length || out.length % 9) throw new Error("Could not read this STL (no complete triangles found).");
    return { positions: new Float32Array(out), indices: null, format: "stl-ascii" };
  }
  function parseOBJ(text) {
    var v = [], idx = [], lines = text.split(/\r?\n/);
    for (var i = 0; i < lines.length; i++) {
      var L = lines[i];
      if (L.charCodeAt(0) === 118 && L.charCodeAt(1) === 32) { // "v "
        var p = L.trim().split(/\s+/); v.push(+p[1], +p[2], +p[3]);
      } else if (L.charCodeAt(0) === 102 && L.charCodeAt(1) === 32) { // "f "
        var f = L.trim().split(/\s+/), ids = [], nv = v.length / 3;
        for (var j = 1; j < f.length; j++) {
          var k = parseInt(f[j], 10); if (isNaN(k)) continue;
          ids.push(k < 0 ? nv + k : k - 1);
        }
        for (var j2 = 1; j2 + 1 < ids.length; j2++) idx.push(ids[0], ids[j2], ids[j2 + 1]); // fan triangulate
      }
    }
    if (!idx.length) throw new Error("No faces found in this OBJ.");
    return { positions: new Float32Array(v), indices: new Uint32Array(idx), format: "obj" };
  }
  var COMP = { 5120: [Int8Array, 1], 5121: [Uint8Array, 1], 5122: [Int16Array, 2], 5123: [Uint16Array, 2], 5125: [Uint32Array, 4], 5126: [Float32Array, 4] };
  var NCOMP = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
  function b64ToBuf(s) {
    if (typeof atob === "function") { var bin = atob(s), u = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; }
    var b = Buffer.from(s, "base64"); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
  }
  function readAccessor(gltf, buffers, ai) {
    var acc = gltf.accessors[ai], bv = gltf.bufferViews[acc.bufferView];
    if (acc.sparse) throw new Error("Sparse glTF accessors are not supported; export as STL.");
    var C = COMP[acc.componentType], nc = NCOMP[acc.type], buf = buffers[bv.buffer];
    var off = (bv.byteOffset || 0) + (acc.byteOffset || 0), stride = bv.byteStride || C[1] * nc;
    var out = new (acc.componentType === 5126 ? Float32Array : Uint32Array)(acc.count * nc);
    var dv = new DataView(buf);
    var get = { 5120: "getInt8", 5121: "getUint8", 5122: "getInt16", 5123: "getUint16", 5125: "getUint32", 5126: "getFloat32" }[acc.componentType];
    for (var i = 0; i < acc.count; i++) for (var c = 0; c < nc; c++) out[i * nc + c] = dv[get](off + i * stride + c * C[1], true);
    return out;
  }
  function mat4mul(a, b) { var o = new Array(16); for (var r = 0; r < 4; r++) for (var c = 0; c < 4; c++) { var s = 0; for (var k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; }
  function nodeMatrix(n) {
    if (n.matrix) return n.matrix.slice();
    var t = n.translation || [0, 0, 0], q = n.rotation || [0, 0, 0, 1], s = n.scale || [1, 1, 1];
    var x = q[0], y = q[1], z = q[2], w = q[3];
    return [(1 - 2 * (y * y + z * z)) * s[0], (2 * (x * y + z * w)) * s[0], (2 * (x * z - y * w)) * s[0], 0,
      (2 * (x * y - z * w)) * s[1], (1 - 2 * (x * x + z * z)) * s[1], (2 * (y * z + x * w)) * s[1], 0,
      (2 * (x * z + y * w)) * s[2], (2 * (y * z - x * w)) * s[2], (1 - 2 * (x * x + y * y)) * s[2], 0,
      t[0], t[1], t[2], 1];
  }
  function gltfToMesh(gltf, buffers) {
    var ext = (gltf.extensionsRequired || []).concat(gltf.extensionsUsed || []);
    if (ext.indexOf("KHR_draco_mesh_compression") >= 0 || ext.indexOf("EXT_meshopt_compression") >= 0)
      throw new Error("This GLB is Draco/meshopt-compressed. Re-export it uncompressed or as STL/OBJ, then check again.");
    var P = [], I = [], base = 0;
    function addMesh(mi, M) {
      gltf.meshes[mi].primitives.forEach(function (pr) {
        if (pr.mode !== undefined && pr.mode !== 4) return; // triangles only
        if (pr.attributes.POSITION === undefined) return;
        var pos = readAccessor(gltf, buffers, pr.attributes.POSITION), nv = pos.length / 3;
        for (var i = 0; i < nv; i++) {
          var x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2];
          P.push(M[0] * x + M[4] * y + M[8] * z + M[12], M[1] * x + M[5] * y + M[9] * z + M[13], M[2] * x + M[6] * y + M[10] * z + M[14]);
        }
        var ind = pr.indices !== undefined ? readAccessor(gltf, buffers, pr.indices) : null;
        if (ind) for (var j = 0; j < ind.length; j++) I.push(ind[j] + base);
        else for (var j2 = 0; j2 < nv; j2++) I.push(j2 + base);
        base += nv;
      });
    }
    function walk(ni, parent) {
      var n = gltf.nodes[ni], M = mat4mul(parent, nodeMatrix(n));
      if (n.mesh !== undefined) addMesh(n.mesh, M);
      (n.children || []).forEach(function (c) { walk(c, M); });
    }
    var I4 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
    var scene = gltf.scenes && gltf.scenes[gltf.scene || 0];
    if (scene && gltf.nodes) scene.nodes.forEach(function (ni) { walk(ni, I4); });
    else (gltf.meshes || []).forEach(function (_, mi) { addMesh(mi, I4); });
    if (!I.length) throw new Error("No triangle meshes found in this glTF/GLB.");
    return { positions: new Float32Array(P), indices: new Uint32Array(I), format: "gltf" };
  }
  function parseGLB(buf) {
    var dv = new DataView(buf);
    if (dv.getUint32(0, true) !== 0x46546c67) throw new Error("Not a GLB file.");
    var off = 12, json = null, bin = null;
    while (off < buf.byteLength) {
      var len = dv.getUint32(off, true), type = dv.getUint32(off + 4, true);
      if (type === 0x4e4f534a) json = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, off + 8, len)));
      else if (type === 0x004e4942) bin = buf.slice(off + 8, off + 8 + len);
      off += 8 + len;
    }
    var buffers = (json.buffers || []).map(function (b, i) {
      if (b.uri === undefined) return bin;
      if (/^data:/.test(b.uri)) return b64ToBuf(b.uri.split(",")[1]);
      throw new Error("This GLB references an external file (" + "buffer " + i + "); export a self-contained GLB.");
    });
    var m = gltfToMesh(json, buffers); m.format = "glb"; return m;
  }
  function parseGLTF(text) {
    var json = JSON.parse(text);
    var buffers = (json.buffers || []).map(function (b) {
      if (b.uri && /^data:/.test(b.uri)) return b64ToBuf(b.uri.split(",")[1]);
      throw new Error("This .gltf uses a separate .bin file. Export a single .glb (or STL) and check that instead.");
    });
    return gltfToMesh(json, buffers);
  }
  function parse(buf, name) {
    var ext = (String(name || "").split(".").pop() || "").toLowerCase();
    var head = new Uint8Array(buf, 0, Math.min(4, buf.byteLength));
    if (ext === "glb" || (head[0] === 0x67 && head[1] === 0x6c && head[2] === 0x54 && head[3] === 0x46)) return parseGLB(buf);
    if (ext === "gltf") return parseGLTF(new TextDecoder().decode(new Uint8Array(buf)));
    if (ext === "obj") return parseOBJ(new TextDecoder().decode(new Uint8Array(buf)));
    if (ext === "stl") return parseSTL(buf);
    throw new Error("Unsupported file type. Use .stl, .obj, .glb or .gltf.");
  }

  /* ---------- analysis ---------- */
  // merge vertices with identical float32 positions (slicers do the same)
  function mergeVertices(pos) {
    var nv = pos.length / 3, cap = 1; while (cap < nv * 2) cap <<= 1;
    var table = new Int32Array(cap).fill(-1), remap = new Uint32Array(nv), out = new Float32Array(pos.length), nu = 0;
    var f32 = new Float32Array(3), u32 = new Uint32Array(f32.buffer);
    for (var i = 0; i < nv; i++) {
      f32[0] = pos[i * 3] + 0; f32[1] = pos[i * 3 + 1] + 0; f32[2] = pos[i * 3 + 2] + 0; // +0 folds -0
      var h = (Math.imul(u32[0], 73856093) ^ Math.imul(u32[1], 19349663) ^ Math.imul(u32[2], 83492791)) & (cap - 1);
      while (true) {
        var e = table[h];
        if (e < 0) { table[h] = nu; out[nu * 3] = f32[0]; out[nu * 3 + 1] = f32[1]; out[nu * 3 + 2] = f32[2]; remap[i] = nu++; break; }
        if (out[e * 3] === f32[0] && out[e * 3 + 1] === f32[1] && out[e * 3 + 2] === f32[2]) { remap[i] = e; break; }
        h = (h + 1) & (cap - 1);
      }
    }
    return { positions: out.slice(0, nu * 3), remap: remap, count: nu };
  }

  function analyze(mesh, opts) {
    opts = opts || {};
    var t0 = Date.now();
    var srcPos = mesh.positions, srcIdx = mesh.indices;
    var nTriRaw = srcIdx ? srcIdx.length / 3 : srcPos.length / 9;
    if (!nTriRaw) throw new Error("The file has no triangles.");
    var mv = mergeVertices(srcPos), V = mv.positions, nV = mv.count;
    // faces on merged vertices
    var F = new Uint32Array(nTriRaw * 3);
    for (var i = 0; i < nTriRaw * 3; i++) F[i] = mv.remap[srcIdx ? srcIdx[i] : i];
    // drop index-degenerate + zero-area faces (rubric v0.2 "export padding")
    var keep = new Uint8Array(nTriRaw), nDeg = 0, nIdxDeg = 0;
    for (var t = 0; t < nTriRaw; t++) {
      var a = F[t * 3], b = F[t * 3 + 1], c = F[t * 3 + 2];
      if (a === b || b === c || a === c) { nDeg++; nIdxDeg++; continue; }
      var ux = V[b * 3] - V[a * 3], uy = V[b * 3 + 1] - V[a * 3 + 1], uz = V[b * 3 + 2] - V[a * 3 + 2];
      var vx = V[c * 3] - V[a * 3], vy = V[c * 3 + 1] - V[a * 3 + 1], vz = V[c * 3 + 2] - V[a * 3 + 2];
      var wx = V[c * 3] - V[b * 3], wy = V[c * 3 + 1] - V[b * 3 + 1], wz = V[c * 3 + 2] - V[b * 3 + 2];
      var cx = uy * vz - uz * vy, cy = uz * vx - ux * vz, cz = ux * vy - uy * vx;
      // same test as trimesh nondegenerate(): longest side and height must both exceed 1e-8
      var Lmax = Math.sqrt(Math.max(ux * ux + uy * uy + uz * uz, vx * vx + vy * vy + vz * vz, wx * wx + wy * wy + wz * wz));
      if (Lmax <= 1e-8 || Math.sqrt(cx * cx + cy * cy + cz * cz) / Lmax <= 1e-8) { nDeg++; continue; }
      keep[t] = 1;
    }
    var nT = nTriRaw - nDeg, G = new Uint32Array(nT * 3);
    for (var t2 = 0, k = 0; t2 < nTriRaw; t2++) if (keep[t2]) { G[k++] = F[t2 * 3]; G[k++] = F[t2 * 3 + 1]; G[k++] = F[t2 * 3 + 2]; }
    F = null; keep = null;
    if (!nT) throw new Error("Every triangle in the file has zero area.");

    // edges: key = (min*nV + max)*2 + dir, sorted
    var keys = new Float64Array(nT * 3);
    for (var f = 0; f < nT; f++) for (var e = 0; e < 3; e++) {
      var p = G[f * 3 + e], q = G[f * 3 + (e + 1) % 3];
      keys[f * 3 + e] = p < q ? (p * nV + q) * 2 : (q * nV + p) * 2 + 1;
    }
    keys.sort();
    var nEdges = 0, boundary = 0, nonManifold = 0, inconsistent = 0, badEdgeKeys = [];
    for (var s = 0; s < keys.length;) {
      var base = Math.floor(keys[s] / 2), e2 = s, fwd = 0;
      while (e2 < keys.length && Math.floor(keys[e2] / 2) === base) { if (keys[e2] % 2 === 0) fwd++; e2++; }
      var cnt = e2 - s; nEdges++;
      if (cnt === 1) boundary++;
      else if (cnt > 2) nonManifold++;
      else if (fwd !== 1) inconsistent++;
      if (cnt !== 2 && badEdgeKeys.length < 400000) badEdgeKeys.push(base, cnt === 1 ? 1 : 2);
      s = e2;
    }
    keys = null;
    var badEdges = new Uint32Array(badEdgeKeys.length / 2 * 2), badKind = new Uint8Array(badEdgeKeys.length / 2);
    for (var bi = 0; bi < badKind.length; bi++) {
      var bk = badEdgeKeys[bi * 2]; badEdges[bi * 2] = Math.floor(bk / nV); badEdges[bi * 2 + 1] = bk % nV; badKind[bi] = badEdgeKeys[bi * 2 + 1];
    }

    // connected parts (union-find on vertices, like trimesh body_count)
    var par = new Int32Array(nV); for (var u = 0; u < nV; u++) par[u] = u;
    function find(x) { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x]; } return x; }
    for (var f2 = 0; f2 < nT; f2++) {
      var r0 = find(G[f2 * 3]), r1 = find(G[f2 * 3 + 1]), r2 = find(G[f2 * 3 + 2]);
      if (r1 !== r0) par[r1] = r0; if (r2 !== r0 && find(r2) !== r0) par[find(r2)] = r0;
    }

    // transform to Z-up mm
    var up = opts.upAxis || (mesh.format === "glb" || mesh.format === "gltf" ? "Y" : "Z");
    var unitScale = UNIT_MM[opts.units || (mesh.format === "glb" || mesh.format === "gltf" ? "m" : "mm")] || 1;
    var mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
    var W = new Float32Array(nV * 3);
    var used = new Uint8Array(nV); for (var g = 0; g < G.length; g++) used[G[g]] = 1;
    for (var vi = 0; vi < nV; vi++) {
      var x = V[vi * 3], y = V[vi * 3 + 1], z = V[vi * 3 + 2], X, Y, Z;
      if (up === "Y") { X = x; Y = -z; Z = y; } else if (up === "X") { X = y; Y = z; Z = x; } else { X = x; Y = y; Z = z; }
      W[vi * 3] = X; W[vi * 3 + 1] = Y; W[vi * 3 + 2] = Z;
      if (!used[vi]) continue;
      if (X < mn[0]) mn[0] = X; if (Y < mn[1]) mn[1] = Y; if (Z < mn[2]) mn[2] = Z;
      if (X > mx[0]) mx[0] = X; if (Y > mx[1]) mx[1] = Y; if (Z > mx[2]) mx[2] = Z;
    }
    var rawLongest = Math.max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]);
    var scale = opts.targetLongestMm > 0 && rawLongest > 0 ? opts.targetLongestMm / rawLongest : unitScale;
    for (var w = 0; w < nV; w++) {
      W[w * 3] = (W[w * 3] - mn[0]) * scale; W[w * 3 + 1] = (W[w * 3 + 1] - mn[1]) * scale; W[w * 3 + 2] = (W[w * 3 + 2] - mn[2]) * scale;
    }
    var dims = [(mx[0] - mn[0]) * scale, (mx[1] - mn[1]) * scale, (mx[2] - mn[2]) * scale];

    // volume, area, bed contact, part min-z
    var vol6 = 0, area = 0, contact = 0, partMinZ = new Map(), partFaces = new Map();
    for (var f3 = 0; f3 < nT; f3++) {
      var ia = G[f3 * 3] * 3, ib = G[f3 * 3 + 1] * 3, ic = G[f3 * 3 + 2] * 3;
      var ax = W[ia], ay = W[ia + 1], az = W[ia + 2], bx = W[ib], by = W[ib + 1], bz = W[ib + 2], qx = W[ic], qy = W[ic + 1], qz = W[ic + 2];
      vol6 += ax * (by * qz - bz * qy) - ay * (bx * qz - bz * qx) + az * (bx * qy - by * qx);
      var e1x = bx - ax, e1y = by - ay, e1z = bz - az, e2x = qx - ax, e2y = qy - ay, e2z = qz - az;
      var nx = e1y * e2z - e1z * e2y, ny = e1z * e2x - e1x * e2z, nz = e1x * e2y - e1y * e2x, nl = Math.sqrt(nx * nx + ny * ny + nz * nz);
      area += nl / 2;
      var zmax = Math.max(az, bz, qz), zmin = Math.min(az, bz, qz);
      if (nl > 0 && zmax <= BED_BAND_MM && nz / nl < -0.7) contact += Math.abs(nz) / 2; // area * |n_z|
      var pr = find(G[f3 * 3]);
      var cur = partMinZ.get(pr); if (cur === undefined || zmin < cur) partMinZ.set(pr, zmin);
      partFaces.set(pr, (partFaces.get(pr) || 0) + 1);
    }
    var watertight = boundary === 0 && nonManifold === 0;
    var parts = partMinZ.size, floating = 0, tinyParts = 0;
    partMinZ.forEach(function (z, key) { if (z > BED_BAND_MM) floating++; if (partFaces.get(key) < 0.01 * nT) tinyParts++; });
    var volume = vol6 / 6;
    var res = {
      format: mesh.format, upAxis: up, units: opts.targetLongestMm > 0 ? "scaled" : (opts.units || (mesh.format === "glb" || mesh.format === "gltf" ? "m" : "mm")),
      scale: scale, triangles: nTriRaw, trianglesChecked: nT, vertices: nV,
      degenerateFaces: nDeg, indexDegenerateFaces: nIdxDeg,
      edges: nEdges, boundaryEdges: boundary, nonManifoldEdges: nonManifold, rubricNonManifoldEdges: boundary + nonManifold,
      inconsistentWindingEdges: inconsistent, watertight: watertight,
      parts: parts, floatingParts: floating, tinyParts: tinyParts,
      dimsMm: dims.map(function (d) { return Math.round(d * 100) / 100; }),
      fitsA1: dims[0] <= A1_BED_MM[0] && dims[1] <= A1_BED_MM[1] && dims[2] <= A1_BED_MM[2],
      volumeMm3: watertight ? Math.round(volume * 10) / 10 : null, signedVolumeMm3: Math.round(volume * 10) / 10,
      insideOut: watertight && volume < 0, areaMm2: Math.round(area * 10) / 10,
      bedContactMm2: Math.round(contact * 10) / 10, ms: Date.now() - t0
    };
    res.verdicts = verdicts(res);
    res.overall = res.verdicts.some(function (v) { return v.level === "fail"; }) ? "fail" : res.verdicts.some(function (v) { return v.level === "warn"; }) ? "warn" : "pass";
    if (opts.withPreview) {
      res.preview = { positions: W, indices: G, badEdges: badEdges, badKind: badKind };
    }
    return res;
  }

  function fmt(n) { return Number(n).toLocaleString("en-US"); }
  function verdicts(r) {
    var v = [];
    v.push(r.watertight
      ? { id: "watertight", level: "pass", title: "Watertight", detail: "Every edge is shared by exactly 2 faces: the slicer sees a closed solid.", fix: "" }
      : { id: "watertight", level: "fail", title: "Not watertight", detail: fmt(r.boundaryEdges) + " open (hole) edges and " + fmt(r.nonManifoldEdges) + " edges shared by 3+ faces. In our benchmark this is a hard fail (score capped at 39).",
        fix: "Blender: 3D-Print Toolbox → Check All, select Non Manifold, then Fill (F) or Make Manifold. MeshLab: Filters → Remeshing → Close Holes." });
    var nm = r.rubricNonManifoldEdges;
    v.push({ id: "nonmanifold", level: nm === 0 ? "pass" : nm <= 5 ? "warn" : "fail",
      title: "Non-manifold edges: " + fmt(nm),
      detail: "Edges not shared by exactly 2 faces (open + 3-way). Rubric v0.2: 0 = full points, 1–5 = half, more than 5 = zero.",
      fix: nm ? "Blender: Select → Select All by Trait → Non Manifold to see them; Mesh → Clean Up → Merge by Distance first. MeshLab: Filters → Cleaning and Repairing → Repair non Manifold Edges." : "" });
    if (r.watertight) {
      var bad = r.inconsistentWindingEdges > 0 || r.insideOut;
      v.push({ id: "normals", level: bad ? "warn" : "pass", title: bad ? "Normals flipped or mixed" : "Normals consistent",
        detail: bad ? (r.insideOut ? "The mesh is inside-out (negative volume)." : "") + (r.inconsistentWindingEdges ? " " + fmt(r.inconsistentWindingEdges) + " edges join faces facing opposite ways." : "") : "All faces wind the same way and point outward.",
        fix: bad ? "Blender: Edit Mode, select all, Mesh → Normals → Recalculate Outside (Shift+N). MeshLab: Filters → Normals → Re-Orient all faces coherently." : "" });
    } else {
      v.push({ id: "normals", level: r.inconsistentWindingEdges ? "warn" : "pass", title: r.inconsistentWindingEdges ? "Some normals flipped" : "Normals consistent where faces meet",
        detail: r.inconsistentWindingEdges ? fmt(r.inconsistentWindingEdges) + " edges join faces facing opposite ways." : "No neighbouring faces face opposite ways (inside/outside can't be confirmed until the mesh is closed).",
        fix: r.inconsistentWindingEdges ? "Blender: Mesh → Normals → Recalculate Outside (Shift+N)." : "" });
    }
    v.push({ id: "parts", level: r.parts === 1 ? "pass" : "warn", title: r.parts === 1 ? "1 connected part" : fmt(r.parts) + " separate parts",
      detail: r.parts === 1 ? "One body, no loose fragments." : (r.tinyParts ? fmt(r.tinyParts) + " are tiny fragments (under 1% of faces) that print as blobs or spaghetti. " : "") + "Fine if the parts are meant to be separate.",
      fix: r.parts === 1 ? "" : "Blender: Mesh → Separate → By Loose Parts, delete the debris. MeshLab: Filters → Cleaning and Repairing → Remove Isolated pieces (wrt Diameter)." });
    if (r.parts > 1) v.push({ id: "floating", level: r.floatingParts ? "warn" : "pass", title: r.floatingParts ? fmt(r.floatingParts) + " part(s) start in mid-air" : "Every part touches the bed",
      detail: r.floatingParts ? "In this orientation they begin more than 0.2 mm above the bed: they need supports or will print as spaghetti." : "No part starts above the first layer.",
      fix: r.floatingParts ? "Join them to the main body (Blender: Boolean Union) or turn on supports in the slicer." : "" });
    v.push({ id: "degenerate", level: r.degenerateFaces ? "warn" : "pass", title: r.degenerateFaces ? fmt(r.degenerateFaces) + " zero-area faces" : "No zero-area faces",
      detail: r.degenerateFaces ? "Dropped before the checks above, as in our benchmark. Usually harmless export padding, but some tools choke on them." : "No collapsed triangles.",
      fix: r.degenerateFaces ? "Blender: Mesh → Clean Up → Degenerate Dissolve. MeshLab: Filters → Cleaning and Repairing → Remove Zero Area Faces." : "" });
    var c = r.bedContactMm2;
    v.push({ id: "bed", level: c >= CONTACT_FULL_MM2 ? "pass" : c > CONTACT_ZERO_MM2 ? "warn" : "fail", title: "Bed contact: " + fmt(c) + " mm²",
      detail: "Flat, down-facing area within 0.2 mm of the bed in this orientation. Rubric v0.2: 10 mm² or less = 0 points, 100 mm²+ = full (benchmark meshes are scaled to 50 mm first).",
      fix: c >= CONTACT_FULL_MM2 ? "" : "Lay it on a flat face in the slicer, cut a flat bottom (Blender: Bisect, then Fill), or add a brim." });
    var L = Math.max.apply(null, r.dimsMm);
    v.push({ id: "fit", level: r.fitsA1 ? (L < 5 ? "warn" : "pass") : "fail", title: r.fitsA1 ? "Fits a Bambu A1 bed" : "Too big for a Bambu A1 bed",
      detail: r.dimsMm.join(" × ") + " mm vs 256 × 256 × 256 mm." + (L < 5 ? " Under 5 mm: check the units." : ""),
      fix: r.fitsA1 ? (L < 5 ? "Pick the right units above (glTF is meters, many AI exports are unit-less)." : "") : "Scale it down in the slicer, pick the right units above, or split it (Blender: Bisect)." });
    return v;
  }

  var API = { parse: parse, parseSTL: parseSTL, parseOBJ: parseOBJ, parseGLB: parseGLB, parseGLTF: parseGLTF, analyze: analyze, verdicts: verdicts, UNIT_MM: UNIT_MM };
  if (typeof module === "object" && module.exports) module.exports = API;
  else root.MeshCheck = API;
  // Web Worker mode
  if (typeof importScripts === "function" && typeof document === "undefined" && typeof self !== "undefined") {
    var cache = null;
    self.onmessage = function (ev) {
      var d = ev.data;
      try {
        if (d.buffer) cache = parse(d.buffer, d.name);
        var r = analyze(cache, { upAxis: d.upAxis, units: d.units, targetLongestMm: d.targetLongestMm, withPreview: true });
        var pv = r.preview; delete r.preview;
        var tp = new Float32Array(pv.positions), ti = new Uint32Array(pv.indices);
        self.postMessage({ ok: true, result: r, preview: { positions: tp, indices: ti, badEdges: pv.badEdges, badKind: pv.badKind } },
          [tp.buffer, ti.buffer, pv.badEdges.buffer, pv.badKind.buffer]);
      } catch (err) { self.postMessage({ ok: false, error: String(err && err.message || err) }); }
    };
  }
})(typeof self !== "undefined" ? self : this);
