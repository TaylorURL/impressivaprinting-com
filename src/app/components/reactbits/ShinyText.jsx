// react-bits ShinyText — a moving specular sweep across text using a clipped
// gradient. Pure CSS (see .rb-shiny in index.css). Great for mono labels.
export default function ShinyText({ text, disabled = false, speed = 4, className = '' }) {
  return (
    <span
      className={`rb-shiny ${disabled ? 'rb-shiny--off' : ''} ${className}`}
      style={{ '--rb-shiny-speed': `${speed}s` }}
    >
      {text}
    </span>
  );
}
