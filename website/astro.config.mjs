import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

/** Prevents Starlight from auto-adding @astrojs/sitemap (broken with Astro 4.16 route API). */
function noopSitemap() {
  return { name: '@astrojs/sitemap', hooks: {} };
}

const site = 'https://khushaljethava.github.io/Anjalikastra';
const description =
  'Anjalikastra is an open-source CLI that crawls any live website and generates a runnable Playwright E2E test suite plus an honest coverage report.';

export default defineConfig({
  site,
  trailingSlash: 'always',
  integrations: [
    noopSitemap(),
    starlight({
      title: 'Anjalikastra',
      description,
      social: {
        github: 'https://github.com/khushaljethava/Anjalikastra',
      },
      editLink: {
        baseUrl: 'https://github.com/khushaljethava/Anjalikastra/edit/main/website/',
      },
      head: [
        {
          tag: 'meta',
          attrs: {
            name: 'keywords',
            content:
              'Anjalikastra, Playwright, E2E testing, web testing, test automation, black-box testing, AI testing, functional tests, smoke tests',
          },
        },
        {
          tag: 'meta',
          attrs: { property: 'og:type', content: 'website' },
        },
        {
          tag: 'meta',
          attrs: { property: 'og:site_name', content: 'Anjalikastra' },
        },
        {
          tag: 'meta',
          attrs: { name: 'twitter:card', content: 'summary_large_image' },
        },
        {
          tag: 'link',
          attrs: { rel: 'canonical', href: site },
        },
      ],
      sidebar: [
        {
          label: 'Start here',
          items: [
            { label: 'Introduction', link: '/' },
            { label: 'Getting Started', link: '/getting-started/' },
            { label: 'CLI Reference', link: '/cli/' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'How It Works', link: '/how-it-works/' },
            { label: 'LLM Providers', link: '/providers/' },
            { label: 'Reports & Output', link: '/output/' },
            { label: 'Caching & Resuming', link: '/caching-resuming/' },
          ],
        },
        {
          label: 'More',
          items: [
            { label: 'FAQ', link: '/faq/' },
            { label: 'Contributing', link: '/contributing/' },
          ],
        },
      ],
    }),
  ],
});
