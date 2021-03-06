uniform sampler2D sPosMap;
uniform sampler2D sStateMap;
uniform sampler2D sColorMap;
uniform vec2 uTexRes;

flat out float deposit;
flat out vec4 color;

/*
	r: age
	g:
	b: heading
	a: deposit
*/
flat out vec4 state;

out Vertex
{
	vec2 texCoord0;
} oVert;

void main() {

	{ // Avoid duplicate variable defs
		vec3 texcoord = TDInstanceTexCoord(uv[0]);
		oVert.texCoord0.st = 2.*texcoord.st-vec2(1.0);
	}

	ivec2 res = ivec2(uTexRes);
	
	ivec2 coord = ivec2(gl_InstanceID%res.x,gl_InstanceID/res.x);

	vec4 posMapData = texelFetch(sPosMap, coord, 0);
	vec4 stateMapData = texelFetch(sStateMap, coord, 0);

	deposit = stateMapData.a;

	state = stateMapData;
	float age = state.r;
	color = texture(sColorMap, vec2(age, 0));

	vec4 worldSpacePos = vec4(P, 1.);
	
	worldSpacePos.xy += posMapData.xy;
	
	gl_Position = TDWorldToProj(worldSpacePos);
	gl_PointSize = 1.;

}
