import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import path from 'node:path';

export async function convertConfig(req, res, kind) {
  // Accept only a same-origin local request with an explicit binary upload.
  if (req.method !== 'POST' || req.headers['content-type'] !== 'application/octet-stream' ||
      (req.headers.origin && req.headers.origin !== 'http://' + req.headers.host)) {
    res.writeHead(403).end(); return;
  }
  let size = 0;
  const chunks = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 64 * 1024 * 1024) { res.writeHead(413).end('配置超过 64 MiB'); return; }
    chunks.push(chunk);
  }
  const bundled = path.join(homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe');
  const python = process.env.CORE_ATLAS_PYTHON || (existsSync(bundled) ? bundled : process.platform === 'win32' ? 'python' : 'python3');
  const child = spawn(python, ['-B', '-X', 'utf8', fileURLToPath(new URL('./profile_input.py', import.meta.url)), kind], {windowsHide:true});
  const output = [], errors = [];
  child.stdout.on('data', chunk => output.push(chunk));
  child.stderr.on('data', chunk => errors.push(chunk));
  child.stdin.on('error', () => {});
  child.on('error', () => res.writeHead(503).end('请设置 CORE_ATLAS_PYTHON 为 Python 3 的路径'));
  child.on('close', code => {
    if (res.writableEnded) return;
    if (code) res.writeHead(400).end('配置转换失败 · ' + Buffer.concat(errors).toString().slice(-400));
    else res.writeHead(200, {'Content-Type':'application/json'}).end(Buffer.concat(output));
  });
  child.stdin.end(Buffer.concat(chunks));
}
