import React, { useEffect, useState, useRef } from 'react';
import RobotViewer3D from './components/RobotViewer3D';
import JointControls from './components/JointControls';
import CartesianJog from './components/CartesianJog';
import ProgramEditor from './components/ProgramEditor';

const App = () => {
  const [robotStatus, setRobotStatus] = useState("DISCONNECTED");
  const [joints, setJoints] = useState({});
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Setup WebSocket
    const connectWs = () => {
      ws.current = new WebSocket(`ws://${window.location.hostname}:8000/ws/robot`);
      
      ws.current.onopen = () => {
        setRobotStatus("CONNECTED");
      };
      
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'robot_state') {
          setJoints(data.joints);
        }
      };
      
      ws.current.onclose = () => {
        setRobotStatus("DISCONNECTED");
        setTimeout(connectWs, 2000);
      };
    };
    
    connectWs();
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const handleEstop = async () => {
    try {
      await fetch(`http://${window.location.hostname}:8000/api/motion/estop`, {
        method: "POST"
      });
      // Optionally show a notification
    } catch (e) {
      console.error("ESTOP Failed:", e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Top Bar */}
      <div className="h-16 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-6 shrink-0">
        <div className="text-xl font-bold tracking-wider">COBOT HMI</div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${robotStatus === 'CONNECTED' ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm font-medium">{robotStatus}</span>
          </div>
          <button 
            onClick={handleEstop}
            className="px-4 py-1.5 bg-red-600 hover:bg-red-700 active:bg-red-800 text-white font-bold rounded shadow-lg transition-colors"
          >
            ESTOP
          </button>
        </div>
      </div>
      
      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col shrink-0">
          <div className="p-4 border-b border-gray-700 cursor-pointer bg-gray-700">Dashboard</div>
          <div className="p-4 border-b border-gray-700 cursor-pointer hover:bg-gray-700">Jogging</div>
          <div className="p-4 border-b border-gray-700 cursor-pointer hover:bg-gray-700">Programs</div>
          <div className="p-4 border-b border-gray-700 cursor-pointer hover:bg-gray-700">Diagnostics</div>
        </div>
        
        {/* Working Area */}
        <div className="flex-1 p-6 overflow-auto">
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-full min-h-[800px]">
            {/* Left column: Controls */}
            <div className="flex flex-col space-y-6">
              <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700">
                <h2 className="text-lg font-bold mb-4 border-b border-gray-700 pb-2">System Readiness</h2>
                <div className="space-y-3">
                  <div className="flex justify-between"><span className="text-gray-400">ROS 2</span><span className="text-green-500">READY</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Gazebo</span><span className="text-green-500">READY</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Controllers</span><span className="text-green-500">READY</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">MoveIt</span><span className="text-green-500">READY</span></div>
                </div>
              </div>
              
              <JointControls currentJoints={joints} />
              <CartesianJog />
            </div>
            
            {/* Middle column: 3D viewer */}
            <div className="bg-gray-800 rounded-lg shadow-lg flex items-center justify-center relative overflow-hidden h-full min-h-[400px]">
               <RobotViewer3D joints={joints} />
            </div>

            {/* Right column: Program Editor */}
            <div className="flex flex-col h-full">
               <ProgramEditor currentJoints={joints} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
