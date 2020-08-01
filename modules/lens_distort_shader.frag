// https://www.shadertoy.com/view/3tXczj

uniform float uK1;
uniform float uK2;
uniform float uK3;
uniform float uDarkEdges;
uniform float uEdge;
uniform float uDispersion;
uniform float uCenterLevel;
uniform float uDispersionExponent;
uniform float uAspectAdjust;

out vec4 fragColor;
void main()
{
    // normalized pixel coordinates (from 0 to 1)
    vec2 uv = vUV.st;
    float aspect = uTDOutputInfo.res.z/uTDOutputInfo.res.w * uAspectAdjust;
   	vec2 distorsion = uv-.5;
    
    distorsion.x*=aspect; // aspect correction
    
    // take distance from center
   	float len = length(distorsion);
    
    // these are the lens parameters
    float k1 = 1.2;
    float k2 = 1.0;
    float k3 = -3.2;
    
    distorsion 
        = distorsion*uK1 
        + distorsion*len*uK2 
        + distorsion*len*len*uK3;
        // higher powers may be added if necessary
    
    
    distorsion.x/=aspect; // aspect correction
    
    vec4 col = texture(sTD2DInputs[0], distorsion+.5);
    
    if (uDarkEdges > 0.5)
    {
    	col *= vec4(
            pow(max(uEdge-len, 0.0), uDispersionExponent),
            pow(max(uEdge-uDispersion-len, 0.0), uDispersionExponent),
            pow(max(uEdge-uDispersion*2-len, 0.0), uDispersionExponent),
        1)*uCenterLevel;
    }
	fragColor = TDOutputSwizzle(col);
}