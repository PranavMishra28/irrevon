/**
 * Serialize structured data for an HTML <script> text node.
 *
 * JSON.stringify alone is not safe in raw script text: HTML parsing recognizes
 * </script> even inside JSON strings. Escaping "<" preserves the decoded JSON
 * value while making that closing tag impossible. The line-separator escapes
 * keep the representation safe for older script parsers and copy/paste tooling.
 */
export const serializeJsonLd = (value: unknown): string =>
  JSON.stringify(value)
    .replaceAll("<", "\\u003c")
    .replaceAll("\u2028", "\\u2028")
    .replaceAll("\u2029", "\\u2029");
