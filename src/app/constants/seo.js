import { ROUTES } from '@constants/routes.js';

// The public origin every canonical, share card and structured-data URL is
// built from. It has to be absolute: a relative og:image is dropped by every
// crawler that reads one.
export const ORIGIN = 'https://www.impressivaprinting.com';
export const OG_IMAGE = `${ORIGIN}/og-card.png`;
export const TWITTER_CARD = 'summary_large_image';

// Titles run 30-60 characters and descriptions 120-160, which is what a result
// row renders before it truncates. No two routes share either.
export const PAGE_META = {
  [ROUTES.home]: {
    title: 'Impressiva Printing | Custom Print Shop in Pasadena',
    description:
      'Custom printing in Pasadena: business cards, vinyl banners, apparel, stickers and signage, proofed before press and finished by hand.',
    breadcrumb: null,
  },
  [ROUTES.products]: {
    title: 'Print Products and Services | Impressiva Printing',
    description:
      'Business cards, banners, apparel, stickers, signage and labels, with the stocks, finishes and turnaround times for each. Quoted on request.',
    breadcrumb: 'Products',
  },
  [ROUTES.work]: {
    title: 'Recent Print Work | Impressiva Printing',
    description:
      'Apparel runs, banners and custom print projects produced for shops, teams and studios across the city, with the client and year behind each.',
    breadcrumb: 'Work',
  },
  [ROUTES.about]: {
    title: 'About the Studio | Impressiva Printing',
    description:
      'From one press in a warehouse room to a full production floor: how Impressiva Printing works, what it runs, and the colour standard it holds.',
    breadcrumb: 'About',
  },
  [ROUTES.contact]: {
    title: 'Contact the Studio | Impressiva Printing',
    description:
      'Request a print quote, or reach the Pasadena studio by phone or email. Opening hours, studio address and what to send with a job enquiry.',
    breadcrumb: 'Contact',
  },
  [ROUTES.privacy]: {
    title: 'Privacy Notice | Impressiva Printing',
    description:
      'What Impressiva Printing stores about an account, an order and the artwork behind it, why each item is kept, and how to have any of it removed.',
    breadcrumb: 'Privacy',
  },
  [ROUTES.terms]: {
    title: 'Terms of Service | Impressiva Printing',
    description:
      'The terms behind a print order at Impressiva Printing: quoting, artwork rights, proofs, colour, turnaround, payment, cancellation and reprints.',
    breadcrumb: 'Terms',
  },
  [ROUTES.login]: {
    title: 'Log In to Your Account | Impressiva Printing',
    description:
      'Sign in to the Impressiva Printing client portal to upload artwork, approve a proof, and follow an order from prepress through to collection.',
    breadcrumb: 'Log In',
    noindex: true,
  },
  [ROUTES.signup]: {
    title: 'Create an Account | Impressiva Printing',
    description:
      'Open an Impressiva Printing account to place print orders, send artwork to the studio, approve proofs, and keep every past job in one place.',
    breadcrumb: 'Create Account',
    noindex: true,
  },
  [ROUTES.forgotPassword]: {
    title: 'Reset Your Password | Impressiva Printing',
    description:
      'Send a reset link to the email on an Impressiva Printing account and choose a new password to get back into the client portal.',
    breadcrumb: 'Reset Password',
    noindex: true,
  },
  [ROUTES.resetPassword]: {
    title: 'Choose a New Password | Impressiva Printing',
    description:
      'Set a new password on an Impressiva Printing account after opening the emailed recovery link, then sign back in to the client portal.',
    breadcrumb: 'New Password',
    noindex: true,
  },
};

export const NOT_FOUND_META = {
  title: 'Page Not Found | Impressiva Printing',
  description:
    'That address does not match a page on the Impressiva Printing site. Head back to the catalogue, the portfolio, or the studio contact details.',
  noindex: true,
};

// Anything behind a sign-in: one title, never indexed, no share card worth
// generating for a page nobody outside the account can open.
export const PRIVATE_META = {
  title: 'Client Portal | Impressiva Printing',
  description:
    'Order status, artwork, proofs and account details for Impressiva Printing customers. Reachable only after signing in to the client portal.',
  noindex: true,
};

const PRIVATE_PREFIXES = [ROUTES.portal, ROUTES.admin, ROUTES.account];

export function metaFor(pathname) {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  if (PRIVATE_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))) {
    return { ...PRIVATE_META, path };
  }
  const known = PAGE_META[path];
  return known ? { ...known, path } : { ...NOT_FOUND_META, path };
}

// Home is always the first crumb, so a route only declares the leaf it adds.
export function breadcrumbFor(meta) {
  if (!meta.breadcrumb || meta.noindex) return null;
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${ORIGIN}/` },
      {
        '@type': 'ListItem',
        position: 2,
        name: meta.breadcrumb,
        item: `${ORIGIN}${meta.path}`,
      },
    ],
  };
}
