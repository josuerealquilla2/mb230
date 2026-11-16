import { writeFile } from 'node:fs/promises';

const fallbackUrl = '/api/v1';
const apiUrl = (process.env.API_URL || fallbackUrl).replace(/\/$/, '');
const target = new URL('../src/environments/environment.vercel.ts', import.meta.url);

const contents = `// Generado automáticamente. No edites este archivo durante el despliegue.
export const environment = {
  production: true,
  apiUrl: ${JSON.stringify(apiUrl)},
};
`;

await writeFile(target, contents, 'utf8');
console.log(`API de producción configurada: ${apiUrl}`);
