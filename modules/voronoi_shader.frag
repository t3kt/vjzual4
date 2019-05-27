// Based on https://www.shadertoy.com/view/ldl3W8

#define BORDER 0
#define FILL 1

layout (location = 0) out vec4 fragColor;
uniform float iGlobalTime;
uniform vec2 uScale;
uniform float rotation;
uniform vec2 translate;
uniform vec2 borderOffset;
uniform vec2 enabled;
uniform vec3 borderColor;
uniform vec2 resolution;

uniform vec4 uBackgroundColor;

uniform float uScaleMapAmount;
uniform vec4 uScaleMapRange; // in low, in high, out low, out high
uniform vec2 uScaleMapChans;

#define SOURCE_RED 1
#define SOURCE_GREEN 2
#define SOURCE_BLUE 3
#define SOURCE_ALPHA 4
#define SOURCE_LUMINANCE 5
#define SOURCE_NONE 0

// https://github.com/AnalyticalGraphicsInc/cesium/blob/master/Source/Shaders/Builtin/Functions/luminance.glsl
float czm_luminance(vec3 rgb)
{
    // Algorithm from Chapter 10 of Graphics Shaders.
    const vec3 W = vec3(0.2125, 0.7154, 0.0721);
    return dot(rgb, W);
}

float map(float value, float inMin, float inMax, float outMin, float outMax) {
  return outMin + (outMax - outMin) * (value - inMin) / (inMax - inMin);
}

vec2 map(vec2 value, vec2 inMin, vec2 inMax, vec2 outMin, vec2 outMax) {
  return outMin + (outMax - outMin) * (value - inMin) / (inMax - inMin);
}

vec3 map(vec3 value, vec3 inMin, vec3 inMax, vec3 outMin, vec3 outMax) {
  return outMin + (outMax - outMin) * (value - inMin) / (inMax - inMin);
}

vec4 map(vec4 value, vec4 inMin, vec4 inMax, vec4 outMin, vec4 outMax) {
  return outMin + (outMax - outMin) * (value - inMin) / (inMax - inMin);
}

float getSourceVal(vec4 sourceColor, int sourceType) {
    if (sourceType >= SOURCE_RED && sourceType <= SOURCE_ALPHA) {
        return sourceColor[sourceType - SOURCE_RED];
    }
    if (sourceType == SOURCE_LUMINANCE) {
        return czm_luminance(sourceColor.rgb);
    }
    return 0.0;
}

vec2 getScaleMapValue(vec2 uv) {
    vec4 scaleMapColor = texture(sTD2DInputs[0], uv);
    vec2 scale = vec2(
        getSourceVal(scaleMapColor, int(uScaleMapChans.r)),
        getSourceVal(scaleMapColor, int(uScaleMapChans.g)));
    return map(
        scale,
        vec2(uScaleMapRange.r),
        vec2(uScaleMapRange.g),
        vec2(uScaleMapRange.b),
        vec2(uScaleMapRange.a));
}

// Created by inigo quilez - iq/2013
// License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.


// I've not seen anybody out there computing correct cell interior distances for Voronoi
// patterns yet. That's why they cannot shade the cell interior correctly, and why you've
// never seen cell boundaries rendered correctly. 

// However, here's how you do mathematically correct distances (note the equidistant and non
// degenerated grey isolines inside the cells) and hence edges (in yellow):

// http://www.iquilezles.org/www/articles/voronoilines/voronoilines.htm

#define ANIMATE

vec2 hash2( vec2 p )
{
	// texture based white noise
	//return texture( resolution.xy, (p+0.5)/256.0 ).xy;
	
    // procedural white noise
	return fract(sin(vec2(dot(p,vec2(127.1,311.7)),dot(p,vec2(269.5,183.3))))*43758.5453);
}

vec3 voronoi( in vec2 x )
{
    vec2 n = floor(x);
    vec2 f = fract(x);

    //----------------------------------
    // first pass: regular voronoi
    //----------------------------------
	vec2 mg, mr;

    float md = 8.0;
    for( int j=-1; j<=1; j++ )
    for( int i=-1; i<=1; i++ )
    {
        vec2 g = vec2(float(i),float(j));
		vec2 o = hash2( n + g );
		#ifdef ANIMATE
        o = 0.5 + 0.5*sin( iGlobalTime + 6.2831*o );
        #endif	
        vec2 r = g + o - f;
        float d = dot(r,r);

        if( d<md )
        {
            md = d;
            mr = r;
            mg = g;
        }
    }

    //----------------------------------
    // second pass: distance to borders
    //----------------------------------
    md = 8.0;
    for( int j=-2; j<=2; j++ )
    for( int i=-2; i<=2; i++ )
    {
        vec2 g = mg + vec2(float(i),float(j));
		vec2 o = hash2( n + g );
		#ifdef ANIMATE
        o = 0.5 + 0.5*sin( iGlobalTime + 6.2831*o );
        #endif	
        vec2 r = g + o - f;

        if( dot(mr-r,mr-r)>0.00001 )
        md = min( md, dot( 0.5*(mr+r), normalize(r-mr) ) );
    }

    return vec3( md, mr );
}

mat2 rotate2d(float _angle){
    return mat2(cos(_angle),-sin(_angle),
                sin(_angle),cos(_angle));
}

void main()
{
	vec2 res = resolution;
    vec2 p = gl_FragCoord.xy/res.xx;


    vec2 scale = uScale;

    if (uScaleMapAmount > 0.0) {
        vec2 mapScale = getScaleMapValue(p);
        scale = mix(scale, mapScale, uScaleMapAmount);
    }
    
    p -= vec2(0.5);
    p *= rotate2d(rotation);
    p *= scale;
    p += translate;
    p += vec2(0.5);
    vec3 c = voronoi( 8.0*p.xy );

    vec4 col = uBackgroundColor;
	// isolines
    //col.rgb = c.x*(0.5 + 0.5*sin(64.0*c.x))*vec3(1.0);
    // borders
    if (enabled[BORDER] > 0.0) {
	    col = mix( vec4(borderColor, 1.0), col, smoothstep( borderOffset[0], borderOffset[1], c.x ) );
    }
    
//    col = texture(sTD2DInputs[0], c.xy).rgb;
	if (enabled[FILL] > 0.0) {
		col.rg += c.xy;
	}
    
    // feature points
	//float dd = length( c.yz );
	//col = mix( vec3(1.0,0.6,0.1), col, smoothstep( 0.0, 0.12, dd) );
	//col += vec3(1.0,0.6,0.1)*(1.0-smoothstep( 0.0, 0.04, dd));

	fragColor = col;



    // DEBUG
//    fragColor = vec4(p, 1.0, 1.0);
//    fragColor = vec4(vUV.st, 1.0, 1.0);
}
