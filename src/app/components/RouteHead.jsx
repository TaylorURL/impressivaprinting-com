import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { OG_IMAGE, ORIGIN, TWITTER_CARD, breadcrumbFor, metaFor } from '@constants/seo.js';

// index.html carries the home page's head so a crawler that runs no script
// still gets a title, a description and a share card. This rewrites that head
// on every route change, which is the only way an SPA gives each URL its own.
const MANAGED = 'data-route-head';

function upsert(tag, keyAttr, keyValue) {
  const selector = `${tag}[${keyAttr}="${keyValue}"]`;
  let el = document.head.querySelector(selector);
  if (!el) {
    el = document.createElement(tag);
    el.setAttribute(keyAttr, keyValue);
    el.setAttribute(MANAGED, '');
    document.head.appendChild(el);
  }
  return el;
}

function setMetaName(name, content) {
  upsert('meta', 'name', name).setAttribute('content', content);
}

function setMetaProperty(property, content) {
  upsert('meta', 'property', property).setAttribute('content', content);
}

export default function RouteHead() {
  const { pathname } = useLocation();

  useEffect(() => {
    const meta = metaFor(pathname);
    const canonical = `${ORIGIN}${meta.path === '/' ? '/' : meta.path}`;

    document.title = meta.title;
    setMetaName('description', meta.description);
    setMetaName('robots', meta.noindex ? 'noindex, follow' : 'index, follow');

    upsert('link', 'rel', 'canonical').setAttribute('href', canonical);

    setMetaProperty('og:type', meta.path === '/' ? 'website' : 'article');
    setMetaProperty('og:site_name', 'Impressiva Printing');
    setMetaProperty('og:title', meta.title);
    setMetaProperty('og:description', meta.description);
    setMetaProperty('og:url', canonical);
    setMetaProperty('og:image', OG_IMAGE);
    setMetaProperty('og:image:width', '1200');
    setMetaProperty('og:image:height', '630');
    setMetaProperty('og:image:alt', 'The Impressiva Printing wordmark on a press-black ground');

    setMetaName('twitter:card', TWITTER_CARD);
    setMetaName('twitter:title', meta.title);
    setMetaName('twitter:description', meta.description);
    setMetaName('twitter:image', OG_IMAGE);

    const crumbs = breadcrumbFor(meta);
    let script = null;
    if (crumbs) {
      script = document.createElement('script');
      script.type = 'application/ld+json';
      script.setAttribute(MANAGED, 'breadcrumb');
      script.textContent = JSON.stringify(crumbs);
      document.head.appendChild(script);
    }

    return () => {
      if (script) script.remove();
    };
  }, [pathname]);

  return null;
}
