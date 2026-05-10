import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'intro',
    'tutorial',
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/installation',
        'getting-started/quick-start',
        'getting-started/configuration',
      ],
    },
    {
      type: 'category',
      label: 'Usage',
      items: [
        'usage/cli',
        'usage/pre-commit',
        'usage/github-actions',
        'usage/whitelist',
        'usage/debug-output',
      ],
    },
    {
      type: 'category',
      label: 'Rules',
      collapsed: false,
      items: [
        {
          type: 'category',
          label: 'Naming',
          items: ['rules/naming/name-pattern'],
        },
        {
          type: 'category',
          label: 'Structure',
          items: [
            'rules/structure/bad-component-reference',
            'rules/structure/component-reference-validation',
          ],
        },
        {
          type: 'category',
          label: 'Performance',
          items: ['rules/performance/polling-interval'],
        },
        {
          type: 'category',
          label: 'Properties',
          items: [
            'rules/properties/unused-custom-properties',
            'rules/properties/excessive-context-data',
          ],
        },
        {
          type: 'category',
          label: 'Scripts',
          items: ['rules/scripts/pylint-script'],
        },
      ],
    },
    {
      type: 'category',
      label: 'Rule Reference',
      collapsed: true,
      items: [
        {
          type: 'category',
          label: 'Naming',
          items: ['reference/naming/name-pattern'],
        },
        {
          type: 'category',
          label: 'Structure',
          items: [
            'reference/structure/bad-component-reference',
            'reference/structure/component-reference-validation',
          ],
        },
        {
          type: 'category',
          label: 'Performance',
          items: ['reference/performance/polling-interval'],
        },
        {
          type: 'category',
          label: 'Properties',
          items: [
            'reference/properties/unused-custom-properties',
            'reference/properties/excessive-context-data',
          ],
        },
        {
          type: 'category',
          label: 'Scripts',
          items: ['reference/scripts/pylint-script'],
        },
      ],
    },
    {
      type: 'category',
      label: 'Developer Guide',
      items: [
        'developing/architecture',
        'developing/creating-rules',
        'developing/api-reference',
        'developing/testing-rules',
        'developing/troubleshooting',
      ],
    },
    'changelog',
  ],
};

export default sidebars;
