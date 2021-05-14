% See this link for the code reference:
% https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/eddy/Faq#How_should_my_--slspec_file_look.3F
% filename = uigetfile('.json','Select JSON file for slice timing');
files = dir('*.json');
for idx = 1:size(files,1)
    filename = files(idx).name;
    outname = [filename(1:end-5),'.slspec'];
    fp = fopen(filename,'r');
    fcont = fread(fp);
    fclose(fp);
    cfcont = char(fcont');
    i1 = strfind(cfcont,'SliceTiming');
    i2 = strfind(cfcont(i1:end),'[');
    i3 = strfind(cfcont((i1+i2):end),']');
    cslicetimes = cfcont((i1+i2+1):(i1+i2+i3-2));
    slicetimes = textscan(cslicetimes,'%f','Delimiter',',');
    [sortedslicetimes,sindx] = sort(slicetimes{1});
    mb = length(sortedslicetimes)/(sum(diff(sortedslicetimes)~=0)+1);
    slspec = reshape(sindx,[mb length(sindx)/mb])'-1;
    dlmwrite(outname,slspec,'delimiter',' ','precision','%3d');
end
