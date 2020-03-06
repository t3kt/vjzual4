// created by florian berger (flockaroo) - 2018
// License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.

// ballpoint line drawing

// drawing a line segment from previous position to actual
// for every particle (ballpoint tip)

#include <common>

float sdLine( vec2 pos, vec2 p1, vec2 p2, float crop )
{
    float l=length(p2-p1);
  	if(l<.001) return 100000.;
    vec2 t=(p2-p1)/l;
    // crop a little from the ends, so subsequent segments will blend together well
    l-=crop;
    p2-=t*crop*.5;
    p1+=t*crop*.5;
  	float pp = dot(pos-p1,t);
  	float pn = dot(pos-p1,t.yx*vec2(1,-1));
  	return max(max(pp-l,-pp),abs(pn));
}

float segDist( int idx, vec2 pos, float crop )
{
    Particle p,pp;
    readParticle(p,idx,sTD2DInputs[0]);
    readParticle(pp,idx+PNUM,sTD2DInputs[0]);
	//vec2 g=getGrad(p.pos,2.5*iResolution.x/600.)*iResolution.x/600.;
    //if(length(g)<.01) return 10000.;

    if(length(pos-p.pos)>25.*uTDOutputInfo.res.z/600.) return 10000.;
    if(length(p.pos-pp.pos)>30.*uTDOutputInfo.res.z/600.) return 10000.;
    return sdLine(pos,p.pos,pp.pos,crop);
}

out vec4 fragColor;
void main()
{
	vec2 fragCoord = vUV.st;
    vec3 col=vec3(0,.2,.65);
    vec3 c=vec3(0);
    float w=1.7*sqrt(uTDOutputInfo.res.z/600.);

    for(int i=0; i<PNUM; i++)
    {
        c+=(-col+1.)*clamp(w*.5-segDist(i,fragCoord,w*.7),0.,1.);
    }
    vec4 color = vec4(col,1);
	fragColor = TDOutputSwizzle(color);

}
