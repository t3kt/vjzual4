flat in float deposit;
flat in vec4 color;
flat in vec4 state;

// Output variable for the color
layout(location = 0) out vec4 oFragColor;
layout(location = 1) out vec4 oStateOut;
void main()
{
	float d = 1.-length( .5 - gl_PointCoord.xy );
	
	//d = pow(d, 1.5);
	vec4 outcol = vec4(deposit);
//	outcol *= d;
	outcol *= color;

	oFragColor = TDOutputSwizzle(outcol);
	oStateOut = state;
}
