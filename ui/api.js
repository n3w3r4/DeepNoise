// All local control requests use this header; cross-origin preflights are not accepted.
async function localFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers, "X-DeepNoise-Request": "1" },
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response;
}
