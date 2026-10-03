import fs from "node:fs/promises";
import path from "node:path";
import openapiTS, { astToString } from "openapi-typescript";

const root = path.resolve(import.meta.dirname, "../../..");
const api = JSON.parse(
  await fs.readFile(path.join(root, "schemas/openapi/v1.json"), "utf8"),
);
const domain = {
  openapi: "3.1.0",
  info: { title: "Checked-in domain contracts", version: "1" },
  paths: {},
  components: { schemas: {} },
};
for (const file of (
  await fs.readdir(path.join(root, "schemas/domain"))
).sort()) {
  const schema = JSON.parse(
    await fs.readFile(path.join(root, "schemas/domain", file), "utf8"),
  );
  Object.assign(domain.components.schemas, schema.$defs ?? {});
  delete schema.$defs;
  domain.components.schemas[schema.title] = schema;
}
const normalized = JSON.parse(
  JSON.stringify(domain).replaceAll("#/$defs/", "#/components/schemas/"),
);
const output = path.resolve(import.meta.dirname, "../src/lib/generated");
await fs.mkdir(output, { recursive: true });
for (const [name, schema] of [
  ["api", api],
  ["domain", normalized],
]) {
  const content =
    "// Generated from checked-in schemas. Run pnpm api:generate; do not edit.\n" +
    astToString(await openapiTS(schema));
  const target = path.join(output, `${name}.ts`);
  if (process.argv.includes("--check")) {
    if ((await fs.readFile(target, "utf8")).replaceAll("\r\n", "\n") !== content)
      throw new Error(`${name} types have drifted; run pnpm api:generate`);
  } else await fs.writeFile(target, content);
}
