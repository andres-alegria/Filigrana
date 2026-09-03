import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { fileURLToPath } from 'node:url';

// Reads directly from the repo-root content/ folder (the content pipeline's
// output) — no copying into src/content/. Excludes _issue.md by pattern.
const articles = defineCollection({
  loader: glob({
    pattern: 'serie-*/vol-*/[0-9][0-9]-*.md',
    base: fileURLToPath(new URL('../../content', import.meta.url)),
    // The glob loader defaults to the front-matter `slug` field as the
    // entry id when present — but that field is title-derived and NOT
    // unique (recurring sections repeat across issues), which silently
    // drops every collision but the last one loaded. Force the id to the
    // file path instead, which is unique by construction.
    generateId: ({ entry }) => entry.replace(/\.md$/, ''),
  }),
  schema: z.object({
    title_es: z.string(),
    title_en: z.string().nullable().optional().default(''),
    // The kicker that sits under the title in the print edition ("TREINTA Y
    // CUATRO AÑOS DESPUES"). It is part of the article's own framing, and had
    // nowhere to live in the body once the pipeline lifted the title out.
    subtitle_es: z.string().nullable().optional().default(''),
    slug: z.string(),
    series: z.number(),
    volume: z.number(),
    issue_date: z.string().nullable().optional(),
    author: z.string(),
    themes: z.array(z.string()).default([]),
    feature_type: z.string(),
    page_start: z.number().nullable().optional(),
    page_end: z.number().nullable().optional(),
    image_count: z.number().default(0),
    summary_es: z.string().nullable().optional().default(''),
    is_featured: z.boolean().optional().default(false),
    has_exhibition: z.boolean().optional().default(false),
    has_audio: z.boolean().optional().default(false),
    lang_available: z.array(z.string()).default(['es']),
    review: z.array(z.string()).default([]),
  }),
});

export const collections = { articles };
