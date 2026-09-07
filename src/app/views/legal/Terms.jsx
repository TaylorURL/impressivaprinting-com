import { SITE } from '@constants/site.js';
import LegalPage, { LegalSection, LegalText } from '@components/layout/LegalPage.jsx';

export default function Terms() {
  return (
    <LegalPage
      kicker="Terms"
      effective="21 August 2026"
      title="Terms of"
      accent="Service"
      intro={`These terms govern print orders placed with ${SITE.name} through ${SITE.domain}. Placing an order accepts them.`}
    >
      <LegalSection title="Quotes and Orders">
        <LegalText>
          A quote covers the stock, finish and quantity it names. Changing any of those after
          approval re-quotes the job. An order is confirmed once the shop accepts it and a proof has
          been approved.
        </LegalText>
      </LegalSection>

      <LegalSection title="Artwork and Rights">
        <LegalText>
          Artwork stays the property of whoever supplied it. Submitting a file confirms the right to
          print it. The shop declines work that infringes a trademark or copyright, and is not
          liable for claims arising from supplied artwork.
        </LegalText>
      </LegalSection>

      <LegalSection title="Proofs">
        <LegalText>
          A digital proof goes out before anything reaches the press. Approving it approves the
          spelling, layout, dimensions and colour breakdown shown. Errors carried through from an
          approved proof are reprinted at cost.
        </LegalText>
      </LegalSection>

      <LegalSection title="Colour">
        <LegalText>
          Presses are G7 calibrated and proofs are checked by hand. Screens and stocks still render
          colour differently, so a close commercial match is what is guaranteed, not an exact one. A
          contract proof is available for jobs where exact colour matters.
        </LegalText>
      </LegalSection>

      <LegalSection title="Turnaround and Delivery">
        <LegalText>
          Production time is counted from proof approval, not from order submission. Standard
          turnaround is three to five working days and rush work goes out the same day where the
          schedule allows. Delivery dates given by a courier are outside the shop&apos;s control.
        </LegalText>
      </LegalSection>

      <LegalSection title="Payment">
        <LegalText>
          Payment falls due on collection or before dispatch unless account terms have been agreed
          in writing. Goods remain the shop&apos;s property until paid for in full.
        </LegalText>
      </LegalSection>

      <LegalSection title="Cancellation and Reprints">
        <LegalText>
          An order can be cancelled without charge until the proof is approved. After that, work
          already run is charged for. Anything that leaves the floor short of the approved proof is
          reprinted or refunded, so tell the shop within ten working days of receipt. Custom-printed
          goods are not returnable otherwise.
        </LegalText>
      </LegalSection>

      <LegalSection title="Accounts">
        <LegalText>
          Account holders are responsible for keeping their sign-in details private and for orders
          placed through their account. The shop closes accounts used for fraudulent or infringing
          work.
        </LegalText>
      </LegalSection>

      <LegalSection title="Liability">
        <LegalText>
          The shop&apos;s liability for any order is limited to the amount paid for it. It does not
          extend to lost profit or to consequential loss.
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
