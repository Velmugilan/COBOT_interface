import React, { useState } from 'react';

const JointControls = ({ currentJoints }: { currentJoints: Record<string, number> }) => {
  // Use current joints as initial targets
  const [targets, setTargets] = useState<Record<string, number>>(currentJoints);
  const [loading, setLoading] = useState(false);
  const [resultMsg, setResultMsg] = useState("");

  const updateTarget = (joint: string, value: number) => {
    setTargets(prev => ({ ...prev, [joint]: value }));
  };

  const handleMove = async () => {
    setLoading(true);
    setResultMsg("Planning...");
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/motion/joint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ joints: targets })
      });
      const data = await res.json();
      if (data.success) {
        setResultMsg("Success");
      } else {
        setResultMsg(`Failed: ${data.message}`);
      }
    } catch (e: any) {
      setResultMsg(`Error: ${e.message}`);
    }
    setLoading(false);
  };

  // Sync targets with current joints if targets are empty
  if (Object.keys(targets).length === 0 && Object.keys(currentJoints).length > 0) {
    setTargets(currentJoints);
  }

  return (
    <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700 mt-6">
      <h2 className="text-lg font-bold mb-4 border-b border-gray-700 pb-2 flex justify-between">
        <span>Joint Jogging (MoveIt 2)</span>
        <span className={resultMsg.includes("Success") ? "text-green-500" : "text-yellow-500"}>{resultMsg}</span>
      </h2>
      
      <div className="space-y-4">
        {Object.entries(currentJoints).map(([name, currentPos]) => {
          const targetPos = targets[name] !== undefined ? targets[name] : currentPos;
          return (
            <div key={name} className="flex items-center space-x-4 bg-gray-900 p-3 rounded">
              <span className="w-16 font-mono text-gray-400">{name}</span>
              
              <button 
                onClick={() => {
                   const newVal = targetPos - 0.1;
                   updateTarget(name, newVal);
                   fetch(`http://${window.location.hostname}:8000/api/motion/jog_joint`, {
                     method: "POST",
                     headers: { "Content-Type": "application/json" },
                     body: JSON.stringify({ joints: { ...targets, [name]: newVal } })
                   }).catch(() => {});
                }}
                className="bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded font-bold"
              >-</button>
              
              <input 
                type="range" 
                min="-3.14" 
                max="3.14" 
                step="0.01" 
                value={targetPos}
                onChange={(e) => updateTarget(name, parseFloat(e.target.value))}
                onMouseUp={async () => {
                   fetch(`http://${window.location.hostname}:8000/api/motion/jog_joint`, {
                     method: "POST",
                     headers: { "Content-Type": "application/json" },
                     body: JSON.stringify({ joints: { ...targets, [name]: targetPos } })
                   }).catch(() => {});
                }}
                className="flex-1"
              />
              
              <button 
                onClick={() => {
                   const newVal = targetPos + 0.1;
                   updateTarget(name, newVal);
                   fetch(`http://${window.location.hostname}:8000/api/motion/jog_joint`, {
                     method: "POST",
                     headers: { "Content-Type": "application/json" },
                     body: JSON.stringify({ joints: { ...targets, [name]: newVal } })
                   }).catch(() => {});
                }}
                className="bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded font-bold"
              >+</button>
              
              <div className="w-24 text-right">
                <span className="text-green-400 font-mono text-sm">{(currentPos as number).toFixed(2)}</span>
                <span className="text-gray-500 font-mono text-sm mx-1">→</span>
                <span className="text-white font-mono text-sm">{targetPos.toFixed(2)}</span>
              </div>
            </div>
          );
        })}
        
        {Object.keys(currentJoints).length === 0 && (
          <div className="text-gray-500 italic text-center py-4">Waiting for robot state...</div>
        )}
      </div>

      <div className="mt-6 flex justify-end">
        <button 
          onClick={() => setTargets(currentJoints)}
          className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded font-bold mr-4"
          disabled={loading}
        >
          Reset Targets
        </button>
        <button 
          onClick={handleMove}
          className={`${loading ? 'bg-blue-800 text-gray-400' : 'bg-blue-600 hover:bg-blue-500'} px-8 py-2 rounded font-bold transition-colors`}
          disabled={loading || Object.keys(targets).length === 0}
        >
          {loading ? 'EXECUTING...' : 'MOVE JOINTS'}
        </button>
      </div>
    </div>
  );
};

export default JointControls;
