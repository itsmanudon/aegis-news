const search = document.querySelector("#search");
const topic = document.querySelector("#topic");
function filter() {
  const query = search.value.trim().toLocaleLowerCase();
  let count = 0;
  for (const story of document.querySelectorAll("[data-story]")) {
    story.hidden =
      !story.dataset.search.includes(query) ||
      (topic.value && story.dataset.topic !== topic.value);
    if (!story.hidden) count++;
  }
  document.querySelector("#search-status").textContent =
    `${count} ${count === 1 ? "Record" : "Records"}`;
  document.querySelector("#no-results").hidden = count !== 0;
}
if (search && topic) {
  search.addEventListener("input", filter);
  topic.addEventListener("change", filter);
}

const encoder = new TextEncoder();
const decode64 = (value) =>
  Uint8Array.from(atob(value), (c) => c.charCodeAt(0));
const hash = async (bytes) =>
  Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
// Manifest values contain strings, integer metadata and arrays. Exact signed and
// content bytes are fetched, avoiding Python/JavaScript floating-point re-encoding.
function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value !== null && typeof value === "object")
    return (
      "{" +
      Object.keys(value)
        .sort()
        .map((key) => JSON.stringify(key) + ":" + canonical(value[key]))
        .join(",") +
      "}"
    );
  return JSON.stringify(value);
}
async function bytes(path) {
  const response = await fetch(path, {
    cache: "no-store",
    credentials: "omit",
  });
  if (!response.ok) throw new Error("Public Evidence File Is Unavailable.");
  return new Uint8Array(await response.arrayBuffer());
}
async function verify(id) {
  if (!crypto.subtle)
    throw new Error("Verification Is Unavailable In This Browser.");
  const prefix = `/data/evidence/${id}/`;
  const [keyBytes, manifestBytes, bodyBytes, metadataBytes, analysisBytes] =
    await Promise.all([
      bytes("/data/public-key.json"),
      bytes(prefix + "manifest.json"),
      bytes(prefix + "signed-body.json"),
      bytes(prefix + "metadata.json"),
      bytes(prefix + "analysis.json"),
    ]);
  const text = (v) => new TextDecoder("utf-8", { fatal: true }).decode(v);
  const publicKey = JSON.parse(text(keyBytes));
  if (
    publicKey.public_key !==
    document.querySelector('meta[name="aegis-public-key"]').content
  ) {
    throw new Error("Public Key Does Not Match This Release’s Trust Anchor.");
  }
  const manifest = JSON.parse(text(manifestBytes));
  const body = JSON.parse(text(bodyBytes));
  const { signature, ...unsigned } = manifest;
  if (
    manifest.version !== "aegis-provenance-1" ||
    manifest.key_id !== "showcase" ||
    publicKey.key_id !== manifest.key_id ||
    publicKey.algorithm !== "Ed25519" ||
    canonical(body) !== canonical(unsigned)
  )
    throw new Error("Signed Manifest Does Not Match.");
  let key;
  try {
    key = await crypto.subtle.importKey(
      "raw",
      decode64(publicKey.public_key),
      { name: "Ed25519" },
      false,
      ["verify"],
    );
  } catch {
    throw new Error("Ed25519 Verification Is Unavailable In This Browser.");
  }
  if (
    !(await crypto.subtle.verify(
      "Ed25519",
      key,
      decode64(signature),
      bodyBytes,
    ))
  )
    throw new Error("Signature Verification Failed.");
  const contents = new Map([
    [id, metadataBytes],
    [id + ":analysis", analysisBytes],
  ]);
  if (manifest.records.length !== 2 || manifest.chain_hashes.length !== 2)
    throw new Error("Incomplete Public Evidence.");
  let previous = "0".repeat(64);
  const seen = new Set();
  const provenanceIds = new Set();
  for (const [index, record] of manifest.records.entries()) {
    if (
      seen.has(record.subject_id) ||
      provenanceIds.has(record.provenance_id) ||
      (index === 0 &&
        (record.operation !== "raw" || record.input_ids.length)) ||
      (index > 0 &&
        (!record.input_ids.length ||
          record.input_ids.some((v) => !seen.has(v))))
    )
      throw new Error("Lineage Verification Failed.");
    const content = contents.get(record.subject_id);
    if (!content || (await hash(content)) !== record.content_hash)
      throw new Error("Published Content Hash Does Not Match.");
    previous = await hash(encoder.encode(canonical({ previous, record })));
    if (previous !== manifest.chain_hashes[index])
      throw new Error("Lineage Hash Does Not Match.");
    seen.add(record.subject_id);
    provenanceIds.add(record.provenance_id);
  }
  return "Verified: Ed25519 Signature, SHA-256 Public Content And Complete Lineage. This Does Not Establish Factual Accuracy.";
}
for (const button of document.querySelectorAll("[data-verify]")) {
  button.addEventListener("click", async () => {
    const status = button.parentElement.querySelector(".verify-status");
    button.disabled = true;
    status.textContent = "Checking Published Bytes…";
    try {
      status.textContent = await verify(button.dataset.verify);
    } catch (error) {
      status.textContent = `Not Verified: ${error.message || "Verification Failed."}`;
    } finally {
      button.disabled = false;
    }
  });
}
