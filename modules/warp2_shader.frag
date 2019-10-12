#define sInput  sTD2DInputs[0]
#define sOffset sTD2DInputs[1]
#define sMask sTD2DInputs[2]

#define DIRMODE_CARTESIAN 0
#define DIRMODE_POLAR 1
uniform int uDirectionMode = DIRMODE_CARTESIAN;

// vec4s: x, y, distance, angle
#define CHAN_NONE 0
#define CHAN_RED 1
#define CHAN_GREEN 2
#define CHAN_BLUE 3
#define CHAN_ALPHA 4
#define CHAN_HUE 5
#define CHAN_SATURATION 6
#define CHAN_VALUE 7
#define CHAN_RGB_AVG 8
#define CHAN_RGBA_AVG 9
uniform ivec4 uCoordChans = ivec4(0, 1, 0, 1);

uniform vec4 uWeight = vec4(0);
uniform vec4 uSourceMidPoint = vec4(0.5);
uniform int uReverse = 0;
uniform float uWeightScale = 1;

uniform int uMaskChan = 0;
uniform vec4 uMaskAmountReverseBlackContrast = vec4(0, 0, 0, 1);
float uMaskAmount = uMaskAmountReverseBlackContrast.r;
float uReverseMask = uMaskAmountReverseBlackContrast.g;
float uMaskBlackLevel = uMaskAmountReverseBlackContrast.b;
float uMaskContrast = uMaskAmountReverseBlackContrast.a;
uniform int uEnableMask = 0;

float applyContrast( float value, float contrast )
{
	return ((value - 0.5) * max(contrast, 0.)) + 0.5;
}

float getChannel(vec4 mapColor, int channel) {
	if (channel == CHAN_NONE) { return 0.0; }
	if (channel == CHAN_RED) { return mapColor.r; }
	if (channel == CHAN_GREEN) { return mapColor.g; }
	if (channel == CHAN_BLUE) { return mapColor.b; }
	if (channel == CHAN_ALPHA) { return mapColor.a; }
	if (channel == CHAN_RGB_AVG) {
		return (mapColor.r + mapColor.g + mapColor.b) / 3.0;
	}
	if (channel == CHAN_RGBA_AVG) {
		return (mapColor.r + mapColor.g + mapColor.b + mapColor.a) / 4.0;
	}
	vec3 hsv = TDRGBToHSV(mapColor.rgb);
	if (channel == CHAN_HUE) { return mapColor.r; }
	if (channel == CHAN_SATURATION) { return mapColor.g; }
	if (channel == CHAN_VALUE) { return mapColor.b; }
	return 0.0;
}

vec2 getCartesianOffset(vec4 mapColor) {
	vec2 offset = vec2(
		getChannel(mapColor, uCoordChans.x),
		getChannel(mapColor, uCoordChans.y)) - uSourceMidPoint.xy;
	return offset * uWeight.xy;
}

vec2 getPolarOffset(vec4 mapColor) {
	vec2 polarOffset = vec2(
		getChannel(mapColor, uCoordChans.z),
		getChannel(mapColor, uCoordChans.q)) - uSourceMidPoint.zw;
	polarOffset *= uWeight.zw;
	float r = polarOffset.x;
	float theta = radians(360 * polarOffset.y);
	return vec2(r * cos(theta), r * sin(theta));
}

layout (location = 0) out vec4 fragColor;
void main() {
	vec2 offset;

	vec4 mapColor = texture(sOffset, vUV.st);
	if (uDirectionMode == DIRMODE_POLAR) {
		offset = getPolarOffset(mapColor);
	} else {
		offset = getCartesianOffset(mapColor);
	}

	if (uEnableMask > 0 && uMaskChan != CHAN_NONE) {
		vec4 maskMapColor = texture(sMask, vUV.st);
		float maskVal = getChannel(maskMapColor, uMaskChan);
		maskVal = applyContrast(maskVal, uMaskContrast);
		maskVal = mix(maskVal, 1-maskVal, uReverseMask);
		if (maskVal < uMaskBlackLevel) {
			maskVal = 0;
		}
		offset = mix(offset, offset*maskVal, uMaskAmount);
	}

	if (uReverse > 0) {
		offset *= -1;
	}
	offset *= uWeightScale;

	fragColor = texture(sInput, vUV.st + offset);
}
