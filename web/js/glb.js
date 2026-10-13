// Minimal .glb reader for the models exported by tools/blender/build_f16.py.
// The bundled three.min.js is a classic (non module) build without GLTFLoader; the files we load are our
// own, so only what the Blender exporter writes is handled: one binary chunk, plain accessors, embedded images.
import { THREE } from './util.js';

const ARRAYS = { 5120: Int8Array, 5121: Uint8Array, 5122: Int16Array, 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array };
const SIZES = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };
const ATTRIBUTES = { POSITION: 'position', NORMAL: 'normal', TEXCOORD_0: 'uv', COLOR_0: 'color' };

// -> { root, materials }: root is a tree of { name, position, quaternion, scale, prims: [{ geometry, material }], children },
// materials are the glTF material definitions with their textures resolved (map, normalMap, ormMap).
export async function parseGLB(buffer) {
  const dv = new DataView(buffer);
  if (dv.getUint32(0, true) !== 0x46546c67) throw new Error('nem .glb fájl');
  const jsonLength = dv.getUint32(12, true);
  const json = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, jsonLength)));
  const bin = 20 + jsonLength + 8;
  const span = (i) => { const v = json.bufferViews[i]; return [bin + (v.byteOffset || 0), v.byteLength, v.byteStride || 0]; };

  const accessor = (i) => {
    const a = json.accessors[i], Type = ARRAYS[a.componentType], n = SIZES[a.type];
    const [offset, , stride] = span(a.bufferView);
    if (stride && stride !== n * Type.BYTES_PER_ELEMENT) throw new Error('interleaved .glb buffers are not supported');
    const start = offset + (a.byteOffset || 0);
    return new THREE.BufferAttribute(new Type(buffer.slice(start, start + a.count * n * Type.BYTES_PER_ELEMENT)), n, !!a.normalized);
  };

  const images = await Promise.all((json.images || []).map(async (im) => {
    const [offset, length] = span(im.bufferView);
    // (an ImageBitmap decodes off the main thread, also while the tab is in the background)
    return createImageBitmap(new Blob([new Uint8Array(buffer, offset, length)], { type: im.mimeType }), { colorSpaceConversion: 'none' });
  }));
  const cache = new Map();
  const texture = (ref, srgb) => {
    if (!ref) return null;
    if (cache.has(ref.index)) return cache.get(ref.index);
    const t = new THREE.Texture(images[json.textures[ref.index].source]);
    t.flipY = false;                                    // glTF: the origin of the UVs is the top left corner (bitmaps are never flipped)
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 8;
    if (srgb) t.encoding = THREE.sRGBEncoding;
    t.needsUpdate = true;
    cache.set(ref.index, t);
    return t;
  };
  const materials = (json.materials || []).map((def) => {
    const pbr = def.pbrMetallicRoughness || {};
    return { name: def.name, def, map: texture(pbr.baseColorTexture, true), normalMap: texture(def.normalTexture, false),
      ormMap: texture(pbr.metallicRoughnessTexture, false) };
  });

  const meshes = (json.meshes || []).map((mesh) => mesh.primitives.map((p) => {
    const geometry = new THREE.BufferGeometry();
    for (const [key, name] of Object.entries(ATTRIBUTES)) if (key in p.attributes) geometry.setAttribute(name, accessor(p.attributes[key]));
    geometry.setIndex(accessor(p.indices));
    geometry.computeBoundingSphere();
    return { geometry, material: p.material };
  }));
  const node = (i) => {
    const n = json.nodes[i];
    return { name: n.name, position: n.translation || [0, 0, 0], quaternion: n.rotation || [0, 0, 0, 1], scale: n.scale || [1, 1, 1],
      prims: n.mesh === undefined ? [] : meshes[n.mesh], children: (n.children || []).map(node) };
  };
  const roots = json.scenes[json.scene || 0].nodes.map(node);
  return { root: roots.length === 1 ? roots[0] : { name: 'scene', position: [0, 0, 0], quaternion: [0, 0, 0, 1], scale: [1, 1, 1], prims: [], children: roots },
    materials };
}
