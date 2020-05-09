// created by florian berger (flockaroo) - 2018
// License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.

// ballpoint line drawing

// some particles (the actual ballpoint tips)

#include <common>
uniform int iFrame;

#define N(v) (v.yx*vec2(1,-1))

void propagate(inout Particle p)
{
    float dt=.02;
    p.pos+=p.vel*dt;
    float sc=(uTDOutputInfo.res.z/800.);

    // gradient, its length, and unit vector
    vec2 g = 1.0*getGrad(p.pos,2.5*sc,sTD2DInputs[2],uTDOutputInfo.res.zw)*sc;
    // add some noise to gradient so plain areas get some texture
    g += (getRand(p.pos/sc,sTD2DInputs[1]).xy-.5)*.003;  //getRand is pixel based so we divide arg by sc so that it looks the same on all scales
    //g+=normalize(p.pos-iResolution.xy*.5)*.001;
    float gl=length(g);
    vec2 gu=normalize(g);

    // calculate velocity change
    vec2 dvel=vec2(0);

    float dir = (float(p.idx%2)*2.-1.); // every 2nd particle is bent left/right

    // apply some randomness to velocity
    dvel += .7*(getRand(p.pos/sc,sTD2DInputs[1]).xy-.5)/(.03+gl*gl)*sc;

    // vel tends towards gradient
    dvel -= 10.*gu*(1.+sqrt(gl*2.))*sc;

    // vel tends towards/away from normal to gradient (every second particle)
    dvel -= 20.*N(gu)/(1.+1.*sqrt(gl*100.))*sc*dir;

    // vel bends right/left (every second particle)
    //dvel += p.vel.yx*vec2(1,-1)*.06;
    dvel += .06*N(p.vel)/(1.+gl*10.)*dir;

    p.vel += dvel;

    // minimum vel
    //p.vel = normalize(p.vel)*max(length(p.vel),30.*sc);

    // anisotropic vel damping
    p.vel-=gu*dot(p.vel,gu)*(.1+2.*gl);
    //p.vel-=gu*dot(p.vel,gu)*.1;
    p.vel-=N(gu)*dot(p.vel,N(gu))*-.02;
    //p.vel*=.95;
}


out vec4 fragColor;
void main()
{
	vec2 fragCoord = vUV.st;
    int lNum = 40;
    Particle p;
    int idx = particleIdx(fragCoord,sTD2DInputs[0]);
    readParticle(p,idx%PNUM,sTD2DInputs[0]);
    if (idx<PNUM)
    {
        propagate(p);
        propagate(p);
        propagate(p);
        int atOnce=PNUM/100;
        //if (int(getRand(iFrame%PNUM).x*float(PNUM/2)) == p.idx/30) p.pos=getRand((iFrame+p.idx)%PNUM).xy*iResolution.xy;
        //if (int(getRand(iFrame).x*float(PNUM/atOnce)) == p.idx/atOnce)
        if ((p.idx+iFrame)%lNum == lNum-1)
        {
            p.pos=getRand(p.idx+iFrame+iFrame/17,sTD2DInputs[1]).yz*uTDOutputInfo.res.zw;
            for(int i=0;i<10;i++) propagate(p);
        }
            //initParticle(p);
    }
	else if (idx>PNUM*2) discard;
    if (iFrame<10) initParticle(p,sTD2DInputs[0],sTD2DInputs[1],iFrame);
    //if (idx>PNUM) { p.pos=vec2(0,0); p.vel=vec2(1,1); readParticle(p,idx-PNUM); }
    writeParticle(p,fragColor,fragCoord,sTD2DInputs[0]);
}
