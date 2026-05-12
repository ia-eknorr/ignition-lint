// Copies the repo-root CHANGELOG.md into docs/changelog.md with frontmatter
// that disables MDX parsing. Plain markdown allows tokens like `<1s` that MDX
// would otherwise reject as malformed JSX. Run as a prebuild step.

const fs = require('fs');
const path = require('path');

const SOURCE = path.resolve(__dirname, '..', '..', 'CHANGELOG.md');
const DEST = path.resolve(__dirname, '..', 'docs', 'changelog.md');

const FRONTMATTER = `---
title: Changelog
sidebar_label: Changelog
description: Release history for ignition-lint
slug: /changelog
---

`;

// MDX 3's parser interprets a `<` followed by anything that could start a tag
// as a JSX expression. Plain text like `<1s` (meaning "less than one second")
// breaks the build. Escape any `<` that is NOT followed by a tag-starting
// character (letter, `!`, `?`, `/`).
function escapeMdxAngleBrackets(source) {
  return source.replace(/<(?![a-zA-Z!?/])/g, '&lt;');
}

const body = fs.readFileSync(SOURCE, 'utf8');
fs.writeFileSync(DEST, FRONTMATTER + escapeMdxAngleBrackets(body));
console.log(`copied ${SOURCE} -> ${DEST}`);
