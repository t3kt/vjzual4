// created by florian berger (flockaroo) - 2018
// License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.

// ballpoint line drawing

// accumulating up the line segments
// slowly fading out older cotent

#include <common>

uniform int iFrame;
out vec4 fragColor;
void main()
{
	vec2 fragCoord = vUV.st;
    vec2 uv = fragCoord.xy / uTDOutputInfo.res.zw;
    //fragColor = max(texture(sTD2DInputs[0],uv),clamp(texture(sTD2DInputs[1],uv)-.003,0.,1.));
    //fragColor = clamp(texture(sTD2DInputs[0],uv)+texture(sTD2DInputs[1],uv)-.003,0.,1.);
    fragColor = (texture(sTD2DInputs[0],uv)+texture(sTD2DInputs[1],uv))*(1.-.006/2000.*float(PNUM));
    fragColor.w=1.;
    if(iFrame<10) fragColor=vec4(0,0,0,1);
}
