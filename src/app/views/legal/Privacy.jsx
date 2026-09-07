import { SITE } from '@constants/site.js';
import LegalPage, { LegalSection, LegalText } from '@components/layout/LegalPage.jsx';

export default function Privacy() {
  return (
    <LegalPage
      kicker="Privacy"
      effective="21 August 2026"
      title="Privacy"
      accent="Notice"
      intro={`This notice covers ${SITE.name} and the account portal at ${SITE.domain}. It describes what the shop stores, why, and how long it keeps it.`}
    >
      <LegalSection title="What the Shop Stores">
        <ul className="space-y-3 text-base leading-relaxed text-ink-950/70">
          <li>
            <span className="font-medium text-ink-950">Account details.</span> An email address and
            password when an account is created, plus the name, company and phone number entered on
            the profile. The password is held by the authentication provider and is never visible to
            the shop.
          </li>
          <li>
            <span className="font-medium text-ink-950">Order records.</span> The product, quantity,
            size, finish, due date and any notes submitted with a job, along with the status history
            as the job moves through production.
          </li>
          <li>
            <span className="font-medium text-ink-950">Artwork.</span> Files uploaded to an order,
            kept so the job can be printed and reprinted.
          </li>
          <li>
            <span className="font-medium text-ink-950">Traffic and fault data.</span> Page visits in
            aggregate, and, when something breaks, the page address, the browser identifier and the
            error message, so the fault can be found and fixed.
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="How It Is Used">
        <LegalText>
          Account and order records exist to quote, produce and deliver print jobs, and to let a
          customer see their own history. Traffic and fault data exist to keep the site working.
          Nothing here is sold, rented, or handed to advertisers, and none of it feeds automated
          decision-making or profiling.
        </LegalText>
      </LegalSection>

      <LegalSection title="Who Else Sees It">
        <LegalText>
          Order and account data sit in a hosted database, and the site itself is served from a
          hosting platform. Both act only on the shop&apos;s instructions. Shop staff see the orders
          they produce. Beyond that, information is disclosed only where the law requires it.
        </LegalText>
      </LegalSection>

      <LegalSection title="Cookies and Storage">
        <LegalText>
          Signing in stores a session token in the browser so the account stays open between visits.
          Clearing site data signs the account out. No advertising or cross-site tracking cookies
          are set.
        </LegalText>
      </LegalSection>

      <LegalSection title="How Long It Is Kept">
        <LegalText>
          Order records and artwork are held while the account is open, so past jobs can be
          reordered. Closing an account removes the account, its profile, its orders and its
          uploaded files.
        </LegalText>
      </LegalSection>

      <LegalSection title="Access and Removal">
        <LegalText>
          Profile details can be corrected from the account page at any time. To request a copy of
          what is held, or to have an account and its records removed, write to{' '}
          <a className="text-flare underline underline-offset-4" href={`mailto:${SITE.email}`}>
            {SITE.email}
          </a>
          .
        </LegalText>
      </LegalSection>

      <LegalSection title="Contact">
        <LegalText>
          {SITE.name}, {SITE.address}. {SITE.phone}.{' '}
          <a className="text-flare underline underline-offset-4" href={`mailto:${SITE.email}`}>
            {SITE.email}
          </a>
          .
        </LegalText>
      </LegalSection>
    </LegalPage>
  );
}
