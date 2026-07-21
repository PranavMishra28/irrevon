/**
 * E1 "Convergence Seat" — the D1 ball-in-V-block seat (path and circle
 * byte-identical to the shipped D1) plus two evidence strokes descending at
 * exactly 45°, parallel to the notch walls, stopping 1.24 units short of the
 * ball: evidence approaches; the claim is already seated and held.
 * Decorative in chrome (aria-hidden with adjacent wordmark); standalone use
 * passes `standalone` to get role="img" + accessible name.
 * Never animated, never used as a spinner.
 */
export function SeatMark({
  size = 20,
  standalone = false,
}: {
  size?: number;
  standalone?: boolean;
}) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      {...(standalone ? { role: "img", "aria-label": "Irrevon" } : { "aria-hidden": true })}
    >
      <path fill="currentColor" d="M2.5 12 H6 L12 18 L18 12 H21.5 V20.5 H2.5 Z" />
      <circle fill="currentColor" cx="12" cy="10.93" r="5" />
      <path fill="none" stroke="currentColor" strokeWidth="2.4" d="M4.1 3 L7.6 6.5" />
      <path fill="none" stroke="currentColor" strokeWidth="2.4" d="M19.9 3 L16.4 6.5" />
    </svg>
  );
}
