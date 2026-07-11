import { useEffect, useRef } from 'react';
import { Renderer, Program, Mesh, Triangle } from 'ogl';

// react-bits Threads — a set of flowing, wavy line "threads" rendered with a
// WebGL fragment shader (ogl). Subtle animated accent for hero/CTA bands.
const VERT = `
attribute vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }
`;

const FRAG = `
precision highp float;
uniform float iTime;
uniform vec3 iResolution;
uniform vec3 uColor;
uniform float uAmplitude;
uniform float uDistance;

const int LINES = 24;

float lineFn(vec2 uv, float y, float amp, float phase, float width) {
  float wave = sin(uv.x * 6.2831 * uDistance + phase + iTime * 0.6) * amp;
  wave += sin(uv.x * 12.0 + phase * 1.7 - iTime * 0.4) * amp * 0.35;
  float d = abs(uv.y - (y + wave));
  return smoothstep(width, 0.0, d);
}

void main() {
  vec2 uv = gl_FragCoord.xy / iResolution.xy;
  float acc = 0.0;
  for (int i = 0; i < LINES; i++) {
    float fi = float(i) / float(LINES - 1);
    float amp = uAmplitude * (0.02 + fi * 0.03);
    float width = 0.0016 + fi * 0.001;
    acc += lineFn(uv, fi, amp, fi * 8.0, width);
  }
  float alpha = clamp(acc, 0.0, 1.0);
  gl_FragColor = vec4(uColor * alpha, alpha);
}
`;

function hexToRgb(hex) {
  const m = hex.replace('#', '');
  return [
    parseInt(m.substring(0, 2), 16) / 255,
    parseInt(m.substring(2, 4), 16) / 255,
    parseInt(m.substring(4, 6), 16) / 255,
  ];
}

export default function Threads({ color = '#e5352b', amplitude = 1, distance = 0.6, className = '' }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    let renderer;
    try {
      renderer = new Renderer({ alpha: true, antialias: true });
    } catch {
      return undefined;
    }
    const gl = renderer.gl;
    gl.clearColor(0, 0, 0, 0);
    container.appendChild(gl.canvas);
    gl.canvas.style.width = '100%';
    gl.canvas.style.height = '100%';
    gl.canvas.style.display = 'block';

    const geometry = new Triangle(gl);
    const program = new Program(gl, {
      vertex: VERT,
      fragment: FRAG,
      uniforms: {
        iTime: { value: 0 },
        iResolution: { value: [1, 1, 1] },
        uColor: { value: hexToRgb(color) },
        uAmplitude: { value: amplitude },
        uDistance: { value: distance },
      },
      transparent: true,
    });
    const mesh = new Mesh(gl, { geometry, program });

    const resize = () => {
      const { clientWidth, clientHeight } = container;
      renderer.setSize(clientWidth || 1, clientHeight || 1);
      program.uniforms.iResolution.value = [gl.canvas.width, gl.canvas.height, 1];
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(container);

    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let raf;
    const start = performance.now();
    const update = (now) => {
      program.uniforms.iTime.value = reduce ? 0 : (now - start) / 1000;
      renderer.render({ scene: mesh });
      raf = requestAnimationFrame(update);
    };
    raf = requestAnimationFrame(update);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      if (gl.canvas.parentElement === container) container.removeChild(gl.canvas);
      const ext = gl.getExtension('WEBGL_lose_context');
      ext?.loseContext();
    };
  }, [color, amplitude, distance]);

  return <div ref={containerRef} className={`h-full w-full ${className}`} />;
}
