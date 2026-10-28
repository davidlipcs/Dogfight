import { createRequire } from 'module';
const require = createRequire(import.meta.url);
globalThis.window = globalThis;
globalThis.THREE = require('./three.cjs');
