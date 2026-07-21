/**
 * D1 "Seat" — ball seated in a 90° V-block; daylight at the apex.
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
      {...(standalone ? { role: "img", "aria-label": "Detent" } : { "aria-hidden": true })}
    >
      <path fill="currentColor" d="M2.5 12 H6 L12 18 L18 12 H21.5 V20.5 H2.5 Z" />
      <circle fill="currentColor" cx="12" cy="10.93" r="5" />
    </svg>
  );
}
