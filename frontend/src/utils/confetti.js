export function triggerConfetti() {
  const canvas = document.createElement('canvas');
  canvas.style.position = 'fixed';
  canvas.style.top = '0';
  canvas.style.left = '0';
  canvas.style.width = '100vw';
  canvas.style.height = '100vh';
  canvas.style.pointerEvents = 'none';
  canvas.style.zIndex = '9999';
  document.body.appendChild(canvas);

  const ctx = canvas.getContext('2d');


  // Set sizing
  const resize = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  };
  resize();
  window.addEventListener('resize', resize);

  const colors = [
    '#f43f5e', '#ec4899', '#d946ef', '#a855f7', '#8b5cf6', 
    '#6366f1', '#3b82f6', '#0ea5e9', '#06b6d4', '#14b8a6', 
    '#10b981', '#22c55e', '#84cc16', '#eab308', '#f97316'
  ];
  const particles = [];

  // Create particles from bottom center and bottom sides
  for (let i = 0; i < 150; i++) {
    const isLeftSide = Math.random() < 0.35;
    const isRightSide = !isLeftSide && Math.random() < 0.5;
    
    let startX = canvas.width / 2;
    let launchDirectionX = (Math.random() - 0.5) * 12;
    
    if (isLeftSide) {
      startX = 20;
      launchDirectionX = Math.random() * 12 + 2; // launch rightwards
    } else if (isRightSide) {
      startX = canvas.width - 20;
      launchDirectionX = -(Math.random() * 12 + 2); // launch leftwards
    }

    particles.push({
      x: startX,
      y: canvas.height + 20,
      radius: Math.random() * 5 + 3,
      color: colors[Math.floor(Math.random() * colors.length)],
      speedX: launchDirectionX,
      speedY: -Math.random() * 18 - 12,
      rotation: Math.random() * 360,
      rotationSpeed: (Math.random() - 0.5) * 12,
      opacity: 1,
      decay: Math.random() * 0.012 + 0.005
    });
  }

  const animate = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let active = false;
    for (const p of particles) {
      if (p.opacity <= 0) continue;
      active = true;

      // Update particle
      p.x += p.speedX;
      p.y += p.speedY;
      p.speedY += 0.38; // gravity
      p.speedX *= 0.98; // wind resistance
      p.rotation += p.rotationSpeed;
      p.opacity -= p.decay;

      // Draw particle
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate((p.rotation * Math.PI) / 180);
      ctx.globalAlpha = Math.max(0, p.opacity);
      ctx.fillStyle = p.color;
      
      ctx.beginPath();
      ctx.fillRect(-p.radius, -p.radius / 2, p.radius * 2, p.radius);
      ctx.restore();
    }

    if (active) {
      requestAnimationFrame(animate);
    } else {
      window.removeEventListener('resize', resize);
      canvas.remove();
    }
  };

  animate();
}
