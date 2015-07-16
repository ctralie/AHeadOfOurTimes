function [vertex, faces, color] = readColorOff(filename)
    fin = fopen(filename);
    fgetl(fin);%COFF
    NFields = str2num(fgetl(fin));
    NVertices = NFields(1)
    NFaces = NFields(2)
    vertex = zeros(3, NVertices);
    color = zeros(3, NVertices);
    faces = zeros(3, NFaces);
    for ii = 1:NVertices
        str = fgetl(fin);
        fields = str2num(str);
        vertex(:, ii) = fields(1:3);
        color(:, ii) = fields(4:6);
    end
    for ii = 1:NFaces
        str = fgetl(fin);
        fields = str2num(str);
        faces(:, ii) = fields(2:4) + 1;%Matlab is 1-indexed
    end
    fclose(fin);
end