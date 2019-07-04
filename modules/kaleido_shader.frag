
uniform float uAngles;
uniform int uFullMode;
uniform vec2 uCenter;
uniform float uRotate;
uniform float uRings;


#ifndef PI
#define PI 3.141592653589793
#endif

vec2 cartesianToPolar(vec2 pos) {
	return vec2(
		length(pos),
		atan(pos.y, pos.x));
}

vec2 polarToCartesian(vec2 pos) {
	return vec2(
		pos.r * cos(pos.g),
		pos.r * sin(pos.g));
}

vec2 kaleidoscope(vec2 uv, float n) {
	float angle = PI / n;

	vec2 polarPos = cartesianToPolar(uv);
	float r = polarPos.r * .5;
	float a = polarPos.g / angle;

	a = mix( fract( a ), 1.0 - fract( a ), mod( floor( a ), 2.0 ) ) * angle;

	return polarToCartesian(vec2(r, a));
}

mat2 rotationZ( in float angle ) {
	return mat2(	cos(angle),		-sin(angle),
					sin(angle),		cos(angle));
}

vec2 polarKaleido(vec2 uv, float angleMult, float radiusMult) {
	vec2 polarPos = cartesianToPolar(uv);
	polarPos.r /= 0.5;
	polarPos.r *= radiusMult;
	polarPos.r = 1.0 - polarPos.r;

	polarPos.g -= PI/2;
	polarPos.g /= PI*2;
	polarPos.g *= angleMult;
	polarPos.g = 1.0 - polarPos.g;
	return polarPos;
}

layout (location = 0) out vec4 fragColor;
void main()
{
	float aspect = uTD2DInfos[0].res.z / uTD2DInfos[0].res.a;
	vec2 center = 2*(uCenter-vec2(0.5, 0.5));
	vec2 uv = 2*(vUV.st-vec2(0.5, 0.5));

	uv.x *= aspect;

	uv -= center;
	uv *= rotationZ(radians(uRotate));
	#ifdef POLAR_MODE
	uv = polarKaleido(uv, uAngles, uRings / 2.0);
//	uv = kaleidoscope(uv, uAngles);
	#else
	uv = kaleidoscope(uv, uAngles);
	#endif
	uv += center;

	if (uFullMode > 0.0) {
		uv *= 2.0;
	} else {
		uv += vec2(0.5);
	}

	uv.x /= aspect;

	#ifdef OUTPUT_UV
		fragColor = vec4(uv, 0.0, 1.0);
	#else
		vec4 color = texture(sTD2DInputs[0], uv);
		fragColor = TDOutputSwizzle(color);
	#endif
}
