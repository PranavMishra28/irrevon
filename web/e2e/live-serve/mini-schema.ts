/**
 * Dependency-free JSON Schema (2020-12 subset) validator for the stub
 * contract test. Implements exactly the keywords the admitted schemas use:
 * type, properties, required, additionalProperties, enum, const, pattern,
 * minLength, minimum, minItems, minProperties, items, oneOf, allOf,
 * if/then/else, not. `format` is annotation-only in 2020-12 and is ignored.
 *
 * The contract spec calibrates this validator against the repo's
 * schemas/examples valid/invalid corpus before trusting it — a vacuous
 * validator fails that calibration, not the payloads.
 */

export interface SchemaObject {
  type?: string | string[];
  properties?: Record<string, Schema>;
  required?: string[];
  additionalProperties?: Schema;
  enum?: unknown[];
  const?: unknown;
  pattern?: string;
  minLength?: number;
  minimum?: number;
  minItems?: number;
  minProperties?: number;
  items?: Schema;
  oneOf?: Schema[];
  allOf?: Schema[];
  if?: Schema;
  then?: Schema;
  else?: Schema;
  not?: Schema;
  [k: string]: unknown;
}

export type Schema = SchemaObject | boolean;

function typeOf(data: unknown): string {
  if (data === null) return "null";
  if (Array.isArray(data)) return "array";
  if (typeof data === "number") return Number.isInteger(data) ? "integer" : "number";
  return typeof data;
}

function matchesType(data: unknown, type: string): boolean {
  const actual = typeOf(data);
  if (type === "number") return actual === "number" || actual === "integer";
  return actual === type;
}

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/** @returns human-readable errors; empty = valid */
export function validate(schema: Schema, data: unknown, path = "$"): string[] {
  if (schema === true) return [];
  if (schema === false) return [`${path}: schema false`];
  const errors: string[] = [];

  if (schema.type !== undefined) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    if (!types.some((t) => matchesType(data, t))) {
      errors.push(`${path}: expected type ${types.join("|")}, got ${typeOf(data)}`);
      return errors; // structural mismatch: deeper keywords are noise
    }
  }

  if (schema.const !== undefined && !same(data, schema.const)) {
    errors.push(`${path}: expected const ${JSON.stringify(schema.const)}`);
  }
  if (schema.enum !== undefined && !schema.enum.some((v) => same(v, data))) {
    errors.push(`${path}: value not in enum`);
  }

  if (typeof data === "string") {
    if (schema.pattern !== undefined && !new RegExp(schema.pattern).test(data)) {
      errors.push(`${path}: pattern ${schema.pattern} failed`);
    }
    if (schema.minLength !== undefined && data.length < schema.minLength) {
      errors.push(`${path}: shorter than minLength ${schema.minLength}`);
    }
  }

  if (typeof data === "number" && schema.minimum !== undefined && data < schema.minimum) {
    errors.push(`${path}: below minimum ${schema.minimum}`);
  }

  if (Array.isArray(data)) {
    if (schema.minItems !== undefined && data.length < schema.minItems) {
      errors.push(`${path}: fewer than minItems ${schema.minItems}`);
    }
    const itemsSchema = schema.items;
    if (itemsSchema !== undefined) {
      data.forEach((item, i) => {
        errors.push(...validate(itemsSchema, item, `${path}[${i}]`));
      });
    }
  }

  if (typeOf(data) === "object") {
    const record = data as Record<string, unknown>;
    const props = schema.properties ?? {};
    for (const key of schema.required ?? []) {
      if (!(key in record)) errors.push(`${path}: missing required "${key}"`);
    }
    if (
      schema.minProperties !== undefined &&
      Object.keys(record).length < schema.minProperties
    ) {
      errors.push(`${path}: fewer than minProperties ${schema.minProperties}`);
    }
    for (const [key, value] of Object.entries(record)) {
      const propSchema = props[key];
      if (propSchema !== undefined) {
        errors.push(...validate(propSchema, value, `${path}.${key}`));
      } else if (schema.additionalProperties === false) {
        errors.push(`${path}: additional property "${key}" not allowed`);
      } else if (
        schema.additionalProperties !== undefined &&
        schema.additionalProperties !== true
      ) {
        errors.push(...validate(schema.additionalProperties, value, `${path}.${key}`));
      }
    }
  }

  for (const sub of schema.allOf ?? []) errors.push(...validate(sub, data, path));
  if (schema.oneOf !== undefined) {
    const passing = schema.oneOf.filter((sub) => validate(sub, data, path).length === 0);
    if (passing.length !== 1) {
      errors.push(`${path}: oneOf matched ${passing.length} schemas (need exactly 1)`);
    }
  }
  if (schema.not !== undefined && validate(schema.not, data, path).length === 0) {
    errors.push(`${path}: matches "not" schema`);
  }
  if (schema.if !== undefined) {
    const condition = validate(schema.if, data, path).length === 0;
    if (condition && schema.then !== undefined) {
      errors.push(...validate(schema.then, data, path));
    }
    if (!condition && schema.else !== undefined) {
      errors.push(...validate(schema.else, data, path));
    }
  }

  return errors;
}
