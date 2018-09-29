// Based on https://www.shadertoy.com/view/Mlcczf by flockaroo

layout (location = 0) out vec4 fragColor;

uniform bool uEnableVignette = false;
uniform float uSpecularAmount = 0.5;
uniform float uSpecularExp = 12.0;

#define iChannel0 sTD2DInputs[0]
#define iChannel1 sTD2DInputs[1]
#define iChannel2 sTD2DInputs[2]
#define iResolution vec2(uTD2DInfos[0].res.zw)

// created by florian berger (flockaroo) - 2018
// License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.

// some relief lighting

#define Res  iResolution.xy
#define Res1 vec2(textureSize(iChannel1,0))

vec4 getRand(vec2 pos) 
{
    vec2 uv=pos/Res1;
    return texture(iChannel1,uv);
}

float getVal(vec2 uv)
{
    float r = getRand(uv*iResolution.xy*.02).x*2.-1.;
    r=0.*exp(-abs(r)/0.05);
    
    return mix(1.,
    //length(textureLod(iChannel0,uv,1.7+.5*log2(iResolution.x/1920.)).xyz)
    length(textureLod(iChannel0,uv,2.5+.5*log2(iResolution.x/1920.)).xyz)*.6+
    length(textureLod(iChannel0,uv,1.5+.5*log2(iResolution.x/1920.)).xyz)*.3+
    length(textureLod(iChannel0,uv,.5+.5*log2(iResolution.x/1920.)).xyz)*.2
    ,1.-r);
}
    
vec2 getGrad(vec2 uv,float delta)
{
    vec2 d=vec2(delta,0);
    return vec2(
        getVal(uv+d.xy)-getVal(uv-d.xy),
        getVal(uv+d.yx)-getVal(uv-d.yx)
    )/delta;
}

void main()
{
    vec2 fragCoord = gl_FragCoord.xy;
    vec2 uv = fragCoord/Res;
    vec3 n = vec3(getGrad(uv,1.0/iResolution.y),150.0);
    //n *= n;
    n=normalize(n);
    fragColor=vec4(n,1);
    vec3 light = normalize(vec3(1,-1,.8));
    float diff=clamp(dot(n,light),0.,1.0);
    float spec=clamp(dot(reflect(light,n),vec3(0,0,-1)),0.0,1.0);
    spec=pow(spec,uSpecularExp)*uSpecularAmount;
    float sh=clamp(dot(reflect(light*vec3(-1,-1,1),n),vec3(0,0,-1)),0.0,1.0);
    sh=pow(sh,4.0)*.1;
    //spec=0.0;
    fragColor = texture(iChannel0,uv)*mix(diff,1.,.8)+spec*vec4(.85,1.,1.15,1.)-sh*vec4(.85,1.,1.15,1.);
    fragColor.w=1.;
    
    if(uEnableVignette)
    {
        vec2 scc=(fragCoord-.5*iResolution.xy)/iResolution.x;
        float vign = 1.3-2.5*dot(scc,scc);
        vign*=1.-.8*exp(-sin(fragCoord.x/iResolution.x*3.1416)*20.);
        vign*=1.-.8*exp(-sin(fragCoord.y/iResolution.y*3.1416)*10.);
        fragColor.xyz *= vign;
    }
    
    //fragColor = texture(iChannel3,fragCoord/Res3);
    // fragColor = texture(iChannel0,fragCoord/Res0);
}

