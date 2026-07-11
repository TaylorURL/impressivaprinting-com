import { useRef } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';

// react-bits TiltedCard — tilts its children in 3D toward the cursor with a
// springy return. Used to give portfolio posters a tactile, held-in-hand feel.
export default function TiltedCard({
  children,
  className = '',
  rotateAmplitude = 10,
  scaleOnHover = 1.03,
}) {
  const ref = useRef(null);
  const rotateX = useSpring(useMotionValue(0), { stiffness: 260, damping: 22 });
  const rotateY = useSpring(useMotionValue(0), { stiffness: 260, damping: 22 });
  const scale = useSpring(1, { stiffness: 260, damping: 22 });

  const handleMove = (e) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const offsetX = e.clientX - rect.left - rect.width / 2;
    const offsetY = e.clientY - rect.top - rect.height / 2;
    rotateX.set((-offsetY / (rect.height / 2)) * rotateAmplitude);
    rotateY.set((offsetX / (rect.width / 2)) * rotateAmplitude);
  };

  const handleEnter = () => scale.set(scaleOnHover);
  const handleLeave = () => {
    scale.set(1);
    rotateX.set(0);
    rotateY.set(0);
  };

  return (
    <motion.div
      ref={ref}
      className={className}
      onMouseMove={handleMove}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      style={{ rotateX, rotateY, scale, transformPerspective: 900, transformStyle: 'preserve-3d' }}
    >
      {children}
    </motion.div>
  );
}
