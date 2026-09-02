/*
 * Puts the rules the first screen needs into the document.
 *
 * The stylesheet is asked for by a link in the head, and a link in the head
 * holds the first paint until the sheet has made its own round trip. The
 * document already carries the first screen as markup, so the rules that
 * markup needs are known at build time. They go into a style block in the
 * head, and the sheet itself is asked for on a media query that matches
 * nothing, fetched without holding the paint, and switched on when it lands.
 * What arrives late is only what the page has no element for yet.
 *
 * The exceptions are the states the page takes on after it is served: a
 * control takes an attribute when it is pressed or current, a section takes
 * one as it is revealed, and none of those are on any element at build time.
 * Every rule keyed on a data- or aria- attribute rides along regardless. So
 * do the font faces: a preloaded font file with no @font-face naming it is
 * text set in the fallback and reset when the sheet lands.
 *
 * Run by `npm run build`, after the bundle exists and before the entry is
 * rewritten to run after the first frame.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import Beasties from 'beasties';

const file = 'dist/index.html';
const inline = new Beasties({
  path: 'dist',
  publicPath: '/',
  preload: 'media',
  pruneSource: false,
  inlineFonts: true,
  preloadFonts: false,
  allowRules: [/\[(data|aria)-/],
  reduceInlineStyles: false,
  mergeStylesheets: false,
  logLevel: 'silent',
});

const html = readFileSync(file, 'utf8');
const out = await inline.process(html);
if (!/<style[^>]*>[\s\S]{200,}<\/style>/.test(out))
  throw new Error('critical-css: no rules were inlined');
if (!/<link[^>]*rel="stylesheet"[^>]*media="print"/.test(out))
  throw new Error('critical-css: the stylesheet still holds the paint');
writeFileSync(file, out.replace(/ data-beasties-container/g, ''));
