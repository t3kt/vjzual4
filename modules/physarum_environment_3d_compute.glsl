// Example Compute Shader

// uniform float exampleUniform;

#define sPositions sTD2DInputs[0]
#define sStates sTD2DInputs[1]
#define sTrail  sTD3DInputs[0]

#define mDepositOut mTDComputeOutputs[0]

layout (local_size_x = 8, local_size_y = 8) in;
void main()
{
	vec4 color;
	//color = texelFetch(sTD2DInputs[0], ivec2(gl_GlobalInvocationID.xy), 0);
	color = vec4(1.0);
	imageStore(mDepositOut, ivec3(gl_GlobalInvocationID.xy, 0), TDOutputSwizzle(color));
}
