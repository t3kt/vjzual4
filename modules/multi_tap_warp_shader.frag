uniform int horzSource;
uniform int vertSource;

uniform vec2 uTapWeights[8];
uniform vec2 sourceMidpoint = vec2(0.5);

#define SOURCE_RED 1
#define SOURCE_GREEN 2
#define SOURCE_BLUE 3
#define SOURCE_ALPHA 4
#define SOURCE_LUMINANCE 5
#define SOURCE_NONE 0

float getSourceVal(vec4 sourceColor, int sourceType) {
    if (sourceType >= SOURCE_RED && sourceType <= SOURCE_ALPHA) {
        return sourceColor[sourceType - SOURCE_RED];
    }
    if (sourceType == SOURCE_LUMINANCE) {
        return czm_luminance(sourceColor.rgb);
    }
    return 0.0;
}

float getOffsetVal(vec4 sourceColor, int sourceType, float weight, float midpoint) {
    float sourceVal;
    if (sourceType >= SOURCE_RED && sourceType <= SOURCE_ALPHA) {
        sourceVal = sourceColor[sourceType - SOURCE_RED];
    } else if (sourceType == SOURCE_LUMINANCE) {
        sourceVal = czm_luminance(sourceColor.rgb);
    } else {
        return 0.0;
    }
    if (sourceVal < midpoint) {
        return map(sourceVal, 0.0, midpoint, -weight, 0.0);
    } else {
        return map(sourceVal, midpoint, 1.0, 0.0, weight);
    }
}

vec2 getTapOffset(vec2 displaceWeight) {
    vec4 sourceColor = texture(sTD2DInputs[1], vUV.st);
    return vec2(
        getOffsetVal(sourceColor, horzSource, displaceWeight.x, sourceMidpoint.x),
        getOffsetVal(sourceColor, vertSource, displaceWeight.y, sourceMidpoint.y));
}

vec4 getWarpTap(vec2 displaceWeight) {
    return texture(sTD2DInputs[0], vUV.st + getTapOffset(displaceWeight));
}

vec4 getZeroTap() {
    return texture(sTD2DInputs[0], vUV.st);
}

vec4 getTapResult(int i) {
    return getWarpTap(uTapWeights[i]);
}
