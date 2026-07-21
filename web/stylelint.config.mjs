/**
 * Token-usage lint: color-bearing longhands must reference a token
 * (var/function/keyword). The token files themselves are the single exempt
 * location for raw values.
 */
export default {
  plugins: ["stylelint-declaration-strict-value"],
  rules: {
    "scale-unlimited/declaration-strict-value": [
      ["/color$/", "background-color", "border-color", "fill", "stroke", "z-index"],
      {
        ignoreValues: ["transparent", "currentColor", "inherit", "none", "auto", "0"],
      },
    ],
  },
  overrides: [
    {
      files: ["src/shared/ui/tokens/*.css"],
      rules: {
        "scale-unlimited/declaration-strict-value": null,
      },
    },
  ],
};
