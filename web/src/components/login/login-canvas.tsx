"use client"

import { Canvas, useFrame } from "@react-three/fiber"
import { useMemo, useRef } from "react"
import * as THREE from "three"

const noiseGlsl = `
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
float snoise(vec3 v) {
  const vec2 C = vec2(1.0/6.0, 1.0/3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(
    i.z + vec4(0.0, i1.z, i2.z, 1.0))
    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
    + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}
`

function GradientOrbs() {
  const meshRef = useRef<THREE.Mesh>(null)
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColor1: { value: new THREE.Color("#0A1628") },
      uColor2: { value: new THREE.Color("#0D3B4F") },
      uColor3: { value: new THREE.Color("#121830") },
      uColor4: { value: new THREE.Color("#2A1A0E") },
    }),
    []
  )

  useFrame((_, delta) => {
    uniforms.uTime.value += delta * 0.15
  })

  return (
    <mesh ref={meshRef} position={[0, 0, -2]}>
      <planeGeometry args={[16, 10, 1, 1]} />
      <shaderMaterial
        uniforms={uniforms}
        vertexShader={`
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `}
        fragmentShader={`
          ${noiseGlsl}
          uniform float uTime;
          uniform vec3 uColor1;
          uniform vec3 uColor2;
          uniform vec3 uColor3;
          uniform vec3 uColor4;
          varying vec2 vUv;
          void main() {
            vec2 uv = vUv;
            float n1 = snoise(vec3(uv * 1.5 + uTime * 0.3, uTime * 0.1)) * 0.5 + 0.5;
            float n2 = snoise(vec3(uv * 2.0 - uTime * 0.2, uTime * 0.15 + 10.0)) * 0.5 + 0.5;
            float n3 = snoise(vec3(uv * 1.0 + uTime * 0.1, uTime * 0.08 + 20.0)) * 0.5 + 0.5;
            vec3 color = mix(uColor1, uColor2, n1);
            color = mix(color, uColor3, n2 * 0.6);
            color = mix(color, uColor4, n3 * 0.15);
            float vignette = 1.0 - smoothstep(0.2, 0.9, length(uv - 0.5) * 1.4);
            color *= 0.6 + vignette * 0.4;
            gl_FragColor = vec4(color, 1.0);
          }
        `}
      />
    </mesh>
  )
}

function Particles() {
  const pointsRef = useRef<THREE.Points>(null)
  const count = 50

  const { positions, speeds } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const spd = new Float32Array(count)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 14
      pos[i * 3 + 1] = (Math.random() - 0.5) * 10
      pos[i * 3 + 2] = -1 + Math.random() * -1
      spd[i] = 0.3 + Math.random() * 0.5
    }
    return { positions: pos, speeds: spd }
  }, [])

  useFrame((state, delta) => {
    if (!pointsRef.current) return
    const posArray = pointsRef.current.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      posArray[i * 3 + 1] += speeds[i] * delta * 0.5
      posArray[i * 3] += Math.sin(state.clock.elapsedTime * 0.5 + i) * delta * 0.05
      if (posArray[i * 3 + 1] > 5.5) {
        posArray[i * 3 + 1] = -5.5
        posArray[i * 3] = (Math.random() - 0.5) * 14
      }
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.03} color="#4A6A7A" transparent opacity={0.25} sizeAttenuation />
    </points>
  )
}

export function LoginCanvas() {
  return (
    <Canvas
      dpr={[1, 1.5]}
      frameloop="always"
      gl={{ antialias: false, alpha: false, powerPreference: "low-power" }}
      camera={{ position: [0, 0, 5], fov: 50 }}
      className="login-scene-enter"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
      }}
      aria-hidden="true"
    >
      <GradientOrbs />
      <Particles />
    </Canvas>
  )
}
