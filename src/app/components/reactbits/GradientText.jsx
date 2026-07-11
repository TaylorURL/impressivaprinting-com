// react-bits GradientText — animated multi-stop gradient clipped to the text,
// with an optional gradient border. Colors default to the flare palette.
export default function GradientText({
  children,
  className = '',
  colors = ['#e5352b', '#f4efe3', '#2f6bff', '#e5352b'],
  animationSpeed = 6,
  showBorder = false,
}) {
  const gradient = {
    backgroundImage: `linear-gradient(90deg, ${colors.join(', ')})`,
    animationDuration: `${animationSpeed}s`,
  };

  return (
    <span className={`rb-gradient ${showBorder ? 'rb-gradient--border' : ''} ${className}`}>
      {showBorder ? <span className="rb-gradient__overlay" style={gradient} aria-hidden /> : null}
      <span className="rb-gradient__text" style={gradient}>
        {children}
      </span>
    </span>
  );
}
