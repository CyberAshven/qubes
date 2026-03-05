import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    'types/index': 'src/types/index.ts',
    'crypto/index': 'src/crypto/index.ts',
    'wallet/index': 'src/wallet/index.ts',
    'blocks/index': 'src/blocks/index.ts',
    'covenant/index': 'src/covenant/index.ts',
    'package/index': 'src/package/index.ts',
    'bcmr/index': 'src/bcmr/index.ts',
    'storage/index': 'src/storage/index.ts',
  },
  format: ['esm', 'cjs'],
  dts: true,
  splitting: true,
  clean: true,
  sourcemap: true,
  treeshake: true,
  outExtension({ format }) {
    return {
      js: format === 'esm' ? '.mjs' : '.cjs',
    };
  },
});
