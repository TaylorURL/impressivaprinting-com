// One photo, offered in two formats at two widths. `src` is the path without
// an extension; the derivatives sit beside it under the same stem, built by
// scripts/images.sh. The browser takes the smallest file its screen and
// decoder can use and the rendered result is the same either way.
//
// `eager` takes the image out of the lazy queue so it starts with the
// document. `priority` is the separate claim that it outranks everything else
// competing for the connection, which only the largest element on the first
// screen can truthfully make; a second image asking for it demotes the first.
export default function Picture({
  src,
  alt,
  width,
  height,
  sizes = '100vw',
  className = '',
  eager = false,
  priority = false,
  widths = [400, 800],
}) {
  const set = (ext) => widths.map((w) => `${src}-${w}.${ext} ${w}w`).join(', ');
  const widest = widths[widths.length - 1];

  return (
    <picture>
      <source type="image/avif" srcSet={set('avif')} sizes={sizes} />
      <img
        src={`${src}-${widest}.webp`}
        srcSet={set('webp')}
        sizes={sizes}
        alt={alt}
        width={width}
        height={height}
        loading={eager ? 'eager' : 'lazy'}
        fetchPriority={priority ? 'high' : 'auto'}
        decoding="async"
        className={className}
      />
    </picture>
  );
}
