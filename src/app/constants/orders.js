// The order pipeline mirrors the process the marketing site promises:
// submit art, proof, production, pickup. `step` drives the stepper;
// canceled sits outside the pipeline entirely.
export const ORDER_STATUSES = {
  'awaiting-artwork': {
    label: 'Awaiting Artwork',
    step: 0,
    tone: 'text-proc-c',
    badge: 'bg-proc-c/10 text-proc-c border-proc-c/30',
    customerHint: 'Upload print-ready files to move this job into review.',
    shopHint: 'Waiting on customer artwork.',
  },
  'in-review': {
    label: 'Artwork Review',
    step: 1,
    tone: 'text-volt',
    badge: 'bg-volt/10 text-volt border-volt/30',
    customerHint: 'Prepress is checking your files.',
    shopHint: 'Check the files and send a proof.',
  },
  proofing: {
    label: 'Proof Approval',
    step: 2,
    tone: 'text-flare',
    badge: 'bg-flare/10 text-flare border-flare/30',
    customerHint: 'Review the proof below, then approve or request changes.',
    shopHint: 'Waiting on the customer to approve the proof.',
  },
  'in-production': {
    label: 'In Production',
    step: 3,
    tone: 'text-proc-y',
    badge: 'bg-proc-y/10 text-proc-y border-proc-y/30',
    customerHint: 'On press.',
    shopHint: 'On press.',
  },
  ready: {
    label: 'Ready for Pickup',
    step: 4,
    tone: 'text-paper-100',
    badge: 'bg-paper-100/10 text-paper-100 border-paper-100/30',
    customerHint: 'Ready for pickup at the studio.',
    shopHint: 'Waiting on pickup.',
  },
  completed: {
    label: 'Completed',
    step: 5,
    tone: 'text-paper-100/40',
    badge: 'bg-paper-100/5 text-paper-100/50 border-paper-100/15',
    customerHint: 'Done.',
    shopHint: 'Closed.',
  },
  canceled: {
    label: 'Canceled',
    step: -1,
    tone: 'text-proc-m',
    badge: 'bg-proc-m/10 text-proc-m border-proc-m/30',
    customerHint: 'This order was canceled.',
    shopHint: 'Canceled.',
  },
};

export const PIPELINE_STEPS = ['Artwork', 'Review', 'Proof', 'Press', 'Ready', 'Done'];

export const ACTIVE_STATUSES = [
  'awaiting-artwork',
  'in-review',
  'proofing',
  'in-production',
  'ready',
];

export const CLOSED_STATUSES = ['completed', 'canceled'];

// Every transition either side can trigger. `label` is what lands on the order
// timeline; `cta` is the button. Note-required actions collect a reason first.
export const ORDER_ACTIONS = {
  'send-proof': {
    to: 'proofing',
    actor: 'shop',
    cta: 'Send Proof',
    label: 'Proof sent for approval',
    variant: 'flare',
    notePrompt: 'Anything the customer should check on this proof? (optional)',
  },
  'request-artwork-changes': {
    to: 'awaiting-artwork',
    actor: 'shop',
    cta: 'Request New Artwork',
    label: 'Changes requested on artwork',
    variant: 'outline',
    noteRequired: true,
    notePrompt: 'Tell the customer what needs fixing: low res, missing bleed, wrong size.',
  },
  'approve-proof': {
    to: 'in-production',
    actor: 'customer',
    cta: 'Approve Proof',
    label: 'Proof approved',
    variant: 'flare',
  },
  'request-proof-changes': {
    to: 'in-review',
    actor: 'customer',
    cta: 'Request Changes',
    label: 'Changes requested on the proof',
    variant: 'outline',
    noteRequired: true,
    notePrompt: 'What should we change on the proof?',
  },
  'start-production': {
    to: 'in-production',
    actor: 'shop',
    cta: 'Send to Press',
    label: 'Moved to press',
    variant: 'outline',
  },
  'mark-ready': {
    to: 'ready',
    actor: 'shop',
    cta: 'Mark Ready',
    label: 'Ready for pickup',
    variant: 'flare',
  },
  complete: {
    to: 'completed',
    actor: 'shop',
    cta: 'Complete Order',
    label: 'Order completed',
    variant: 'flare',
  },
  cancel: {
    to: 'canceled',
    actor: 'shop',
    cta: 'Cancel Order',
    label: 'Order canceled by the shop',
    variant: 'ghost',
    confirm: 'Cancel this order? This cannot be undone.',
  },
  'customer-cancel': {
    to: 'canceled',
    actor: 'customer',
    cta: 'Cancel Order',
    label: 'Order canceled by the customer',
    variant: 'ghost',
    confirm: 'Cancel this order? This cannot be undone.',
  },
};

export const SHOP_ACTIONS = {
  'awaiting-artwork': ['cancel'],
  'in-review': ['send-proof', 'request-artwork-changes', 'start-production', 'cancel'],
  proofing: ['start-production', 'cancel'],
  'in-production': ['mark-ready', 'cancel'],
  ready: ['complete'],
  completed: [],
  canceled: [],
};

export const CUSTOMER_ACTIONS = {
  'awaiting-artwork': ['customer-cancel'],
  'in-review': [],
  proofing: ['approve-proof', 'request-proof-changes'],
  'in-production': [],
  ready: [],
  completed: [],
  canceled: [],
};
