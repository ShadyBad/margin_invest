"use client"

import { useRef, useMemo, useState, useEffect } from "react"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { Color, ShaderMaterial, Vector2 } from "three"

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`

const fragmentShader = `
  precision highp float;

  uniform float uTime;
  uniform float uScrollProgress;
  uniform float uTempo;
  uniform float uDensity;
  uniform vec3 uBaseColor;
  uniform vec3 uMidColor;
  uniform vec3 uAccentColor;
  uniform vec2 uResolution;
  uniform vec2 uMouse;

  varying vec2 vUv;

  // Simplex 3D noise
  vec4 permute(vec4 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
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
    i = mod(i, 289.0);
    vec4 p = permute(permute(permute(
      i.z + vec4(0.0, i1.z, i2.z, 1.0))
      + i.y + vec4(0.0, i1.y, i2.y, 1.0))
      + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 1.0/7.0;
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
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
  }

  void main() {
    vec2 uv = vUv;
    float aspect = uResolution.x / uResolution.y;
    vec2 st = vec2(uv.x * aspect, uv.y);

    // Mouse parallax (subtle)
    vec2 mouseOffset = (uMouse - 0.5) * 0.05;
    st += mouseOffset;

    float time = uTime * uTempo * 0.08;

    // Layer 1: Large slow movement
    float n1 = snoise(vec3(st * 1.5, time * 0.5)) * 0.5 + 0.5;

    // Layer 2: Medium detail
    float n2 = snoise(vec3(st * 3.0 + 100.0, time * 0.7)) * 0.5 + 0.5;

    // Layer 3: Fine detail (density-controlled)
    float n3 = snoise(vec3(st * 6.0 + 200.0, time)) * 0.5 + 0.5;
    float detailMix = uDensity * 0.3;

    // Blend noise layers
    float noise = n1 * 0.5 + n2 * 0.3 + n3 * detailMix;

    // Color gradient
    vec3 color = mix(uBaseColor, uMidColor, noise);
    color = mix(color, uAccentColor, n2 * 0.3);

    // Caustic highlights
    float caustic = pow(n1 * n2, 3.0) * 1.5;
    color += vec3(0.93, 0.91, 0.89) * caustic * 0.12;

    // Scroll dimming
    float dim = 1.0 - uScrollProgress * 0.8;
    color *= dim;

    // Vignette
    vec2 vigUv = vUv * 2.0 - 1.0;
    float vig = 1.0 - dot(vigUv * 0.5, vigUv * 0.5);
    color *= smoothstep(0.0, 0.7, vig);

    gl_FragColor = vec4(color, 1.0);
  }
`

interface FluidMeshProps {
  baseColor: string
  midColor: string
  accentColor: string
  tempo: number
  density: number
  scrollProgress: number
}

function FluidMesh({
  baseColor,
  midColor,
  accentColor,
  tempo,
  density,
  scrollProgress,
}: FluidMeshProps) {
  const materialRef = useRef<ShaderMaterial>(null)
  const { size } = useThree()
  const mouse = useRef(new Vector2(0.5, 0.5))

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uScrollProgress: { value: 0 },
      uTempo: { value: tempo },
      uDensity: { value: density },
      uBaseColor: { value: new Color(baseColor) },
      uMidColor: { value: new Color(midColor) },
      uAccentColor: { value: new Color(accentColor) },
      uResolution: { value: new Vector2(size.width, size.height) },
      uMouse: { value: new Vector2(0.5, 0.5) },
    }),
    // Only recreate on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  useFrame(({ clock }) => {
    if (!materialRef.current) return
    materialRef.current.uniforms.uTime.value = clock.getElapsedTime()
    materialRef.current.uniforms.uScrollProgress.value = scrollProgress
    materialRef.current.uniforms.uTempo.value = tempo
    materialRef.current.uniforms.uDensity.value = density
    materialRef.current.uniforms.uBaseColor.value.set(baseColor)
    materialRef.current.uniforms.uMidColor.value.set(midColor)
    materialRef.current.uniforms.uAccentColor.value.set(accentColor)
    materialRef.current.uniforms.uResolution.value.set(size.width, size.height)
    materialRef.current.uniforms.uMouse.value.copy(mouse.current)
  })

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
      />
    </mesh>
  )
}

interface FluidShaderProps {
  baseColor?: string
  midColor?: string
  accentColor?: string
  tempo?: number
  density?: number
  scrollProgress?: number
}

export function FluidShader({
  baseColor = "#0F0D0B",
  midColor = "#1A5A3E",
  accentColor = "#1A7A5A",
  tempo = 1.0,
  density = 0.5,
  scrollProgress = 0,
}: FluidShaderProps) {
  const [isDesktop, setIsDesktop] = useState(false)

  useEffect(() => {
    const mql = window.matchMedia("(min-width: 768px)")
    setIsDesktop(mql.matches)

    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mql.addEventListener("change", handler)
    return () => mql.removeEventListener("change", handler)
  }, [])

  if (!isDesktop) return null

  return (
    <Canvas
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
      }}
      gl={{ antialias: false, alpha: false }}
      dpr={1}
    >
      <FluidMesh
        baseColor={baseColor}
        midColor={midColor}
        accentColor={accentColor}
        tempo={tempo}
        density={density}
        scrollProgress={scrollProgress}
      />
    </Canvas>
  )
}
