import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'Anjalikastra',
      description: 'Autonomous web testing agent — point it at a URL, get a runnable Playwright test suite.',
      logo: { src: './src/assets/logo.png' },
      social: {
        github: 'https://github.com/khushaljethava/Anjalikastra',
      },
      sidebar: [
        { label: 'Home', link: '/' },
        {
          label: 'Documentation',
          autogenerate: { directory: 'docs' },
        },
      ],
    }),
  ],
  site: 'https://khushaljethava.work/Anjalikastra/',
});
