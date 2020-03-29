/*
	r: pos.x
	g: pos.y
	b: heading
	a: deposit
*/
layout (location = 0) out vec4 fragColor;

/*
	r: age
	g:
	b:
	a:
*/
layout (location = 1) out vec4 stateOut;

uniform float uSensorAngle;
uniform float uRotationAngle;
uniform float uSeed;
uniform float uStepSize;
uniform float uSensorDistanceOffset;
uniform float uPctRandomDir;
uniform float uStepSizeMultiplier;
uniform float uAspect;
uniform vec2 uTrailThresholds;
uniform vec2 uDepositThresholds;
uniform float uKillPct;
uniform float uDepositAmt;
uniform float uAgeStep;
uniform float uSensorMapAmount;
uniform float uAngleWeightAmount;



float rand(vec2 st) {
    return fract(sin(dot(st.xy,
                         vec2(12.9898,78.233)))*
        43758.5453123);
}

#define PI 3.141592653589793
#define TWOPI 6.28318530718

#define sPositions sTD2DInputs[0]
#define sTrail  sTD2DInputs[1]
#define sResetData sTD2DInputs[2]
#define sStates sTD2DInputs[3]
#define sSensorOffsetMap sTD2DInputs[4]
#define sAngleWeightMap sTD2DInputs[5]

float adjustAngle(float angle) {
	if (uAngleWeightAmount == 0) {
		return angle;
	}
	float coord = mod(angle, TWOPI) / TWOPI;
//	float coord = angle / TWOPI;
	float mapAngle = texture(sAngleWeightMap, vec2(coord, 0)).r * TWOPI;
	return mix(angle, mapAngle, uAngleWeightAmount);
}

void main() {
	stateOut = vec4(0.0, 0.0, 0.0, 1.0);

	#if (Randomkilltoggle==1)
	float randkillVal = rand(vUV.ts + vec2(1.546456*uSeed, 1.108645678*uSeed));
	if (randkillVal < uKillPct) {
		fragColor = texture(sResetData, vUV.st);
		return;
	}
	#endif

    vec4 data = texture(sPositions, vUV.st);
    vec2 pos = data.xy;
    pos.x /= uAspect;
    
    float heading = data.z;
    
    float angleA = heading + uSensorAngle;
    float angleB = heading;
    float angleC = heading - uSensorAngle;

		float sensorOffset = uSensorDistanceOffset;
		float sensorOffsetFromMap = texture(sSensorOffsetMap, pos.xy).r * uSensorDistanceOffset;
		sensorOffset = mix(sensorOffset, sensorOffsetFromMap, uSensorMapAmount);
    vec2 tex = uTD2DInfos[1].res.xy * sensorOffset;
    vec2 uvA = pos.xy + tex * vec2(cos(angleA),sin(angleA));
    vec2 uvB = pos.xy + tex * vec2(cos(angleB),sin(angleB));
    vec2 uvC = pos.xy + tex * vec2(cos(angleC),sin(angleC));
    
    vec4 senA = texture(sTrail, uvA);
    vec4 senB = texture(sTrail, uvB);
    vec4 senC = texture(sTrail, uvC);
    
    float r1 = rand(vUV.ts + vec2(1.13646*uSeed, 1.3261564*uSeed));
    
    if (r1 < uPctRandomDir) {
    	// rotate randomly left or right by rotation angle
    	heading += rand(vUV.st + vec2(uSeed, uSeed)) > .5 ? -uRotationAngle : uRotationAngle;
    }
    else if ((senB.r > senA.r) && (senB.r > senC.r)) {
    	// stay facing same direction	
    }
    else if ((senB.r < senA.r) && (senB.r < senC.r)) {
    	// rotate randomly left or right by rotation angle
    	heading += rand(vUV.st + vec2(uSeed, uSeed)) > .5 ? -uRotationAngle : uRotationAngle;
    }
    else if (senA.r < senC.r) {
    	// rotate right by RA
    	heading -= uRotationAngle;
    }
    else if (senC.r < senA.r) {
    	// rotate left by RA
    	heading += uRotationAngle;
    }
    else {
    	// continue facing same direction
    }
		heading = adjustAngle(heading);
    
    vec2 tempVec = tex * vec2(cos(heading),sin(heading));
    vec2 tempPos = pos + uStepSize * tempVec;
    
    vec4 newData = texture(sTrail, tempPos.xy);
    
    float doDeposit = smoothstep(uDepositThresholds.x, uDepositThresholds.y, newData.r);
    if (doDeposit == 0.) {
    	heading = rand(vUV.ts + vec2(-uSeed, uSeed))*TWOPI;
    }
    
    float actualStepSize = uStepSize * mix(1., uStepSizeMultiplier, smoothstep(uTrailThresholds.x, uTrailThresholds.y, newData.r));

    pos.xy += actualStepSize * tempVec;
    
    #if (Boundarybehavior==0) // clamp
    pos.xy = clamp(pos.xy, vec2(0.), vec2(1.));
    #elif (Boundarybehavior==1) // repeat
    pos.xy = fract(pos.xy);
    #elif (Boundarybehavior==2) // respawn
    if (pos.x < 0. || pos.x > 1. || pos.y < 0. || pos.y > 1.) {
    	fragColor = texture(sResetData, vUV.st);
    	return;
    }
    #endif
    
    pos.x *= uAspect;
        
    fragColor = vec4(pos, heading, doDeposit*uDepositAmt);
		stateOut = texture(sStates, vUV.st);
	stateOut.r += uAgeStep;
}
