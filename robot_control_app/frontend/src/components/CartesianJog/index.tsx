import React, { useState } from 'react';

const CartesianJog = () => {
  const [loading, setLoading] = useState(false);
  const [resultMsg, setResultMsg] = useState("");
  const [stepSize, setStepSize] = useState(0.01); // default 10mm

  const handleJog = async (axis: string, direction: number) => {
    setLoading(true);
    setResultMsg("Planning...");
    
    // In a real implementation, we would query the current TCP pose,
    // apply the delta, and send the new pose target to MoveIt.
    // For this prototype, we'll send a relative move command if the backend supports it.
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/motion/cartesian`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          axis: axis, 
          distance: direction * stepSize 
        })
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

  return (
    <div className="bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700 mt-6 flex-1">
      <h2 className="text-lg font-bold mb-4 border-b border-gray-700 pb-2 flex justify-between">
        <span>Cartesian Jogging</span>
        <span className={resultMsg.includes("Success") ? "text-green-500" : "text-yellow-500"}>{resultMsg}</span>
      </h2>
      
      <div className="mb-4">
        <label className="text-sm text-gray-400 mr-4">Step Size:</label>
        <select 
          className="bg-gray-700 text-white p-1 rounded" 
          value={stepSize} 
          onChange={(e) => setStepSize(parseFloat(e.target.value))}
        >
          <option value={0.001}>1 mm</option>
          <option value={0.01}>10 mm</option>
          <option value={0.05}>50 mm</option>
          <option value={0.1}>100 mm</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-8 mb-6">
        {/* Translation */}
        <div>
          <h3 className="text-gray-400 text-sm mb-2 text-center">Translation (XYZ)</h3>
          <div className="grid grid-cols-3 gap-2 max-w-[200px] mx-auto">
             <div/>
             <button disabled={loading} onClick={() => handleJog('x', 1)} className="bg-gray-700 hover:bg-gray-600 p-2 rounded font-bold">X+</button>
             <div/>
             <button disabled={loading} onClick={() => handleJog('y', 1)} className="bg-gray-700 hover:bg-gray-600 p-2 rounded font-bold">Y+</button>
             <div className="flex items-center justify-center font-bold text-gray-500">XY</div>
             <button disabled={loading} onClick={() => handleJog('y', -1)} className="bg-gray-700 hover:bg-gray-600 p-2 rounded font-bold">Y-</button>
             <div/>
             <button disabled={loading} onClick={() => handleJog('x', -1)} className="bg-gray-700 hover:bg-gray-600 p-2 rounded font-bold">X-</button>
             <div/>
          </div>
          <div className="flex justify-center space-x-4 mt-4">
             <button disabled={loading} onClick={() => handleJog('z', 1)} className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded font-bold w-full">Z+</button>
             <button disabled={loading} onClick={() => handleJog('z', -1)} className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded font-bold w-full">Z-</button>
          </div>
        </div>

        {/* Rotation */}
        <div>
          <h3 className="text-gray-400 text-sm mb-2 text-center">Rotation (Roll/Pitch/Yaw)</h3>
          <div className="flex flex-col space-y-3">
             <div className="flex items-center justify-between bg-gray-900 p-2 rounded">
                <span className="font-mono text-gray-400 w-8">RX</span>
                <button disabled={loading} onClick={() => handleJog('rx', -1)} className="bg-gray-700 hover:bg-gray-600 px-4 py-1 rounded font-bold">-</button>
                <button disabled={loading} onClick={() => handleJog('rx', 1)} className="bg-gray-700 hover:bg-gray-600 px-4 py-1 rounded font-bold">+</button>
             </div>
             <div className="flex items-center justify-between bg-gray-900 p-2 rounded">
                <span className="font-mono text-gray-400 w-8">RY</span>
                <button disabled={loading} onClick={() => handleJog('ry', -1)} className="bg-gray-700 hover:bg-gray-600 px-4 py-1 rounded font-bold">-</button>
                <button disabled={loading} onClick={() => handleJog('ry', 1)} className="bg-gray-700 hover:bg-gray-600 px-4 py-1 rounded font-bold">+</button>
             </div>
             <div className="flex items-center justify-between bg-gray-900 p-2 rounded">
                <span className="font-mono text-gray-400 w-8">RZ</span>
                <button disabled={loading} onClick={() => handleJog('rz', -1)} className="bg-gray-700 hover:bg-gray-600 px-4 py-1 rounded font-bold">-</button>
                <button disabled={loading} onClick={() => handleJog('rz', 1)} className="bg-gray-700 hover:bg-gray-600 px-4 py-1 rounded font-bold">+</button>
             </div>
          </div>
        </div>
      </div>
      
      {/* End Effector */}
      <div className="border-t border-gray-700 pt-4">
        <h3 className="text-gray-400 text-sm mb-3">End Effector</h3>
        <div className="flex space-x-4">
            <button 
                disabled={loading} 
                onClick={async () => {
                    setLoading(true); setResultMsg("Opening...");
                    try {
                        const res = await fetch(`http://${window.location.hostname}:8000/api/gripper/open`, { method: "POST" });
                        const data = await res.json();
                        setResultMsg(data.success ? "Success" : "Failed");
                    } catch (e: any) { setResultMsg(`Error: ${e.message}`); }
                    setLoading(false);
                }} 
                className="bg-blue-600 hover:bg-blue-500 py-3 rounded font-bold flex-1 shadow-lg transition-colors"
            >
                OPEN GRIPPER
            </button>
            <button 
                disabled={loading} 
                onClick={async () => {
                    setLoading(true); setResultMsg("Closing...");
                    try {
                        const res = await fetch(`http://${window.location.hostname}:8000/api/gripper/close`, { method: "POST" });
                        const data = await res.json();
                        setResultMsg(data.success ? "Success" : "Failed");
                    } catch (e: any) { setResultMsg(`Error: ${e.message}`); }
                    setLoading(false);
                }} 
                className="bg-amber-600 hover:bg-amber-500 py-3 rounded font-bold flex-1 shadow-lg transition-colors"
            >
                CLOSE GRIPPER
            </button>
        </div>
      </div>
    </div>
  );
};

export default CartesianJog;
