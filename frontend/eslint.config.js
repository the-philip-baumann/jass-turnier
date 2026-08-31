import pluginVue from "eslint-plugin-vue";
import skipFormatting from "@vue/eslint-config-prettier";
import globals from "globals";

export default [
  {
    name: "app/files-to-lint",
    files: ["**/*.{js,mjs,jsx,vue}"],
  },
  {
    name: "app/files-to-ignore",
    ignores: ["**/dist/**", "**/node_modules/**", "**/coverage/**"],
  },
  ...pluginVue.configs["flat/essential"],
  {
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
  },
  {
    // Route views are addressed by their route, not used as <TagName/> elsewhere,
    // so single-word names are fine here.
    files: ["src/views/**/*.vue"],
    rules: {
      "vue/multi-word-component-names": "off",
    },
  },
  skipFormatting,
];
