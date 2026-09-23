const expoConfig = require('eslint-config-expo/flat');

module.exports = [
  ...expoConfig,
  {
    // design/ is mirrored output from Open Design, not our source.
    ignores: ['node_modules/**', '.expo/**', 'dist/**', 'android/**', 'ios/**', 'design/**'],
  },
  {
    rules: {
      'import/no-unresolved': 'off',
      // i18next's default export intentionally carries the same names as its
      // named exports; the rule fires on documented usage.
      'import/no-named-as-default-member': 'off',
    },
  },
];
