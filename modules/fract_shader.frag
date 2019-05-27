layout (location = 0) out vec4 fragColor;

uniform float uScale;
uniform vec2 uOffset;
uniform float uRotate;
uniform vec2 uFold;
uniform float uDotScale;
uniform float uDotOffset;
uniform float uColDisp;
uniform float uColDispMix;
uniform int uIterations;
uniform float uCoordMix;
uniform float uTanGain;

mat2 rotMatrixXY(float r)
{
	float s = sin(radians(r));
	float c = cos(radians(r));
	
	return mat2(c,	s,
				-s,	c);
}

mat2 rot = rotMatrixXY(uRotate);
float outputAspect = uTDOutputInfo.res.x / uTDOutputInfo.res.y;
float invAspect = 1.0 / outputAspect;
vec2 offset = uOffset * (uScale - 1.0);

vec4 inputCol = vec4(0.0);

void processP(inout vec2 p, in vec2 basePos);

void main()
{

	vec2 p = (2 * vUV.st - 1.0);
	p.y *=  outputAspect;
	//p += (uOffset * (uScale - 1.0));
	
	inputCol = texture(sTD2DInputs[0], vUV.st);
	
	vec2 basePos = p;
	
	for (int i = 0; i < uIterations; i++)
	{
		processP(p, basePos);
		p *= rot;
	}

	p.y *= invAspect;
	p = 0.5 * p + .5;
	p = mix(vUV.st, p, uCoordMix);
	inputCol = texture(sTD2DInputs[0], p);

	fragColor = inputCol;
}

void noop(vec2 p) {}
void noop(vec2 p, float d) {}

#define S1A noop

void S1B(inout vec2 p) {
	p = abs(p) - uFold; //standard fold
}
void S1C(inout vec2 p) {
	p = (1 - abs(p)) - uFold;
}
void S1D(inout vec2 p) {
	p = (1 - abs(p)) - uFold - abs(p -uFold);
}

#define S2A noop

void S2B(inout vec2 p) {
	p = (1 - abs(p)) - uFold - (abs(p)+uFold);
}

void S2C(inout vec2 p) {
	p = abs(p - uFold) - abs(p + uFold) + p;
}

void S2D(inout vec2 p) {
	p = p - abs(p - uFold) + abs(p + uFold);
}

#define S4A noop

void S4BDot(inout vec2 p, in float d) {
	p -= (d - uDotOffset) * uDotScale;
}

#define S5A noop

void S5B(inout vec2 p) {
	p = mod(p, 1.0);
}

void S5C(inout vec2 p) {
	p = mod(p, 1.0) + abs(p);
}

void S5DDisp(inout vec2 p) {
	p += inputCol.xy * uColDisp;
}

void S5EDisp(inout vec2 p) {
	p *= mix(vec2(1.0), inputCol.xy * uColDisp, uColDispMix);
}

void S6ADisp(inout vec2 p) {
	p += texture(sTD2DInputs[0], .5 * p + .5).xy * uColDisp;
}

void S6BDisp(inout vec2 p) {
	p *= mix(vec2(1.0), texture(sTD2DInputs[0], .5 * p + .5).xy * uColDisp, uColDispMix);
}

#define S7A noop

void S7BTan(inout vec2 p) {
	p += tan(p) * uTanGain;
}

#define S9A noop

void S9B(inout vec2 p) {
	p = mod(p, 1.0) + abs(p);
}

void S9C(inout vec2 p) {
	p = mod(p, 1.0);
}


//--INSERT-SECTION-DEFS

#ifndef S1
	#define S1	S1A
#endif
#ifndef S2
	#define S2	S2A
#endif
#ifndef S4
	#define S4	S4A
#endif
#ifndef S5
	#define S5	S5A
#endif
#ifndef S6
	#define S6	S6ADisp
#endif
#ifndef S7
	#define S7	S7A
#endif
#ifndef S9
	#define S9	S9A
#endif

void processP(inout vec2 p, in vec2 basePos) {
	S1(p);

	S2(p);

	// S3 modes were both the same:
	float d = dot(p, basePos);

	S4(p, d);

	S5(p);

	S6(p);

	S7(p);

	// S8 modes were both the same:
	p = p * uScale - offset;

	S9(p);
}
