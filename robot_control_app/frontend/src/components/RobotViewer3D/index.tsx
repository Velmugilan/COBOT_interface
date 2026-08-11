import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Environment } from '@react-three/drei';
import * as THREE from 'three';
import URDFLoader from 'urdf-loader';

const URDFRobot = ({ joints }: { joints: Record<string, number> }) => {
  const [robot, setRobot] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // We fetch the main arm.urdf.xacro. However, urdf-loader doesn't natively parse xacro macros.
    // In a real application, you'd run xacro to generate the compiled URDF xml and serve that via FastAPI.
    // For this demonstration, we'll try to load a compiled version if available, or just mock the visual.
    // Since we mounted /ros_packages/arm_description, we can fetch from it.
    
    // In ROS, it's common to serve a pre-compiled URDF for web viewers.
    const loadRobot = async () => {
      try {
        const manager = new THREE.LoadingManager();
        const loader = new URDFLoader(manager);
        
        // This requires a static URDF file without xacro macros.
        // Assuming the backend provides a compiled URDF at /api/robot/description
        const res = await fetch(`http://${window.location.hostname}:8000/api/robot/description`);
        if (!res.ok) {
           throw new Error("Could not fetch compiled URDF");
        }
        const xml = await res.text();
        
        loader.packages = {
          'arm_description': `http://${window.location.hostname}:8000/ros_packages/arm_description`
        };
        
        const parsedRobot = loader.parse(xml);
        
        // Fix up rotations/materials
        parsedRobot.rotation.x = -Math.PI / 2;
        parsedRobot.traverse((child: any) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
            if (!child.material) {
               child.material = new THREE.MeshStandardMaterial({ color: 0x888888 });
            }
          }
        });
        
        setRobot(parsedRobot);
      } catch (e: any) {
        console.warn("Could not load URDF via API. Falling back to basic visualization.", e);
        setError(e.message);
      }
    };
    
    loadRobot();
  }, []);

  // Update joint angles every frame
  useFrame(() => {
    if (robot && joints) {
      Object.keys(joints).forEach(jointName => {
        if (robot.joints[jointName]) {
          robot.joints[jointName].setAngle(joints[jointName]);
        }
      });
    }
  });

  if (error) {
    return (
       <group>
         <mesh position={[0, 0.5, 0]}>
            <boxGeometry args={[0.2, 1, 0.2]} />
            <meshStandardMaterial color="orange" />
         </mesh>
         <mesh position={[0, 1.2, 0]}>
            <sphereGeometry args={[0.15, 32, 32]} />
            <meshStandardMaterial color="red" />
         </mesh>
       </group>
    );
  }

  return robot ? <primitive object={robot} /> : null;
};

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, errorMsg: string}> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, errorMsg: "" };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, errorMsg: error.message };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full w-full text-center p-6 text-gray-400">
           <svg className="w-16 h-16 mb-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
           <h3 className="text-xl font-bold text-white mb-2">3D Viewer Unavailable</h3>
           <p>Your browser or system does not support WebGL hardware acceleration.</p>
           <p className="text-xs mt-4 text-red-400 font-mono">{this.state.errorMsg}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

const RobotViewer3D = ({ joints }: { joints: Record<string, number> }) => {
  return (
    <div className="w-full h-full relative bg-gray-900 rounded-lg overflow-hidden border border-gray-700 shadow-inner">
      <ErrorBoundary>
        <Canvas shadows camera={{ position: [2, 1.5, 2], fov: 45 }} gl={{ antialias: false, powerPreference: "low-power" }}>
          <color attach="background" args={['#111827']} />
          
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
          <directionalLight position={[-10, 10, -5]} intensity={0.5} />
          
          <Environment preset="city" />
          
          <URDFRobot joints={joints} />
          
          <Grid 
            infiniteGrid 
            fadeDistance={10} 
            sectionColor="#374151" 
            cellColor="#1f2937" 
            position={[0, -0.01, 0]} 
          />
          
          <OrbitControls 
            makeDefault 
            minPolarAngle={0} 
            maxPolarAngle={Math.PI / 2 + 0.1}
            target={[0, 0.5, 0]} 
          />
          
          <axesHelper args={[1]} />
        </Canvas>
      </ErrorBoundary>
    </div>
  );
};

export default RobotViewer3D;
