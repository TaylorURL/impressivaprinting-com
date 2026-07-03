import { Check } from 'lucide-react';

// Placeholder job tracker — a demo of order status, no backend.
const STAGES = ['Received', 'Proofing', 'In Production', 'Ready'];

const DEMO_JOBS = [
  { id: 'JOB-4471', name: 'Foil Business Cards ×500', stage: 3, eta: 'Ready for pickup' },
  { id: 'JOB-4468', name: 'Vinyl Banner 6×3ft', stage: 2, eta: 'Ships tomorrow' },
  { id: 'JOB-4455', name: 'Team Hoodies ×24', stage: 1, eta: 'Proof sent — awaiting approval' },
];

function Stepper({ stage }) {
  return (
    <div className="flex items-center">
      {STAGES.map((label, i) => {
        const done = i <= stage;
        const active = i === stage;
        return (
          <div key={label} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center">
              <span
                className={`grid h-7 w-7 place-items-center rounded-full border text-[10px] font-700 ${
                  done
                    ? 'border-flare bg-flare text-white'
                    : 'border-paper-100/25 text-paper-100/40'
                } ${active ? 'animate-bar-pulse' : ''}`}
              >
                {done ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : i + 1}
              </span>
              <span
                className={`spec mt-2 hidden text-[9px] uppercase tracking-[0.12em] sm:block ${
                  done ? 'text-paper-100/70' : 'text-paper-100/35'
                }`}
              >
                {label}
              </span>
            </div>
            {i < STAGES.length - 1 ? (
              <span
                className={`mx-1 h-px flex-1 sm:mx-2 ${i < stage ? 'bg-flare' : 'bg-paper-100/15'}`}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

export default function JobTracker() {
  return (
    <div className="mt-14">
      <div className="flex items-center justify-between border-b border-paper-100/12 pb-3">
        <span className="kicker text-paper-100/50">Active Jobs</span>
        <span className="spec text-xs text-flare">Demo</span>
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-3">
        {DEMO_JOBS.map((job) => (
          <div key={job.id} className="border border-paper-100/12 bg-ink-900 p-6">
            <div className="flex items-center justify-between">
              <span className="spec text-xs tracking-[0.15em] text-flare">{job.id}</span>
              <span className="spec text-[10px] uppercase tracking-[0.15em] text-paper-100/40">
                {STAGES[job.stage]}
              </span>
            </div>
            <p className="mt-3 font-head text-lg font-700 text-paper-100">{job.name}</p>
            <div className="mt-6">
              <Stepper stage={job.stage} />
            </div>
            <p className="spec mt-5 text-[11px] text-paper-100/50">{job.eta}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
